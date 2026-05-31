from __future__ import annotations

import discord
from discord import app_commands
from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.service import get_effective_profile_stats
from clash_mmo.game.heroes import get_total_hero_power
from clash_mmo.game.matchmaking.battle import calculate_power
from clash_mmo.game.state import load_mmo_state, update_mmo_state
from clash_mmo.game.territory import (
    TERRITORY_REGIONS,
    add_conquest_points,
    claim_region,
    collect_region_income,
    format_territory_map,
    resolve_conquest,
)

# Base power floors so low-level players can still participate.
_ATTACKER_BASE_POWER = 10
_DEFENDER_BASE_POWER = 15  # slight defender advantage


def register_territory_commands(bot, ctx):

    async def _state():
        data = await load_mmo_state(ctx)
        data.setdefault("territories", {})
        return data

    @bot.tree.command(name="territorymap", description="View the clan territory map")
    async def territorymap(interaction: discord.Interaction):
        data = await _state()
        embed = discord.Embed(
            title="🗺️ Clan Territory Map",
            description=format_territory_map(data["territories"]),
            color=0x2ECC71,
        )
        embed.add_field(
            name="What territories do",
            value=(
                "Territories are clan-owned regions that generate shared Gold income. "
                "Claim regions, attack enemy regions, then collect income with `/territoryincome`."
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="claimterritory", description="Claim a territory region")
    @app_commands.describe(region_id="Territory region")
    async def claimterritory(interaction: discord.Interaction, region_id: str):
        region_id = region_id.strip().lower()

        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message("❌ Invalid region.", ephemeral=True)
            return

        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

        def _update(state):
            territories = state.setdefault("territories", {})
            claim_region(territories, region_id, clan_name)
            add_conquest_points(territories, clan_name, 100)
            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(f"🏴 {clan_name} claimed {TERRITORY_REGIONS[region_id]['name']}")

    @bot.tree.command(name="attackterritory", description="Attack a territory region")
    @app_commands.describe(region_id="Territory region")
    async def attackterritory(interaction: discord.Interaction, region_id: str):
        # Defer immediately: gear stat computation + state loads can exceed
        # Discord's 3-second window. Deferring prevents 10062 errors.
        await interaction.response.defer()
        region_id = region_id.strip().lower()

        if region_id not in TERRITORY_REGIONS:
            await interaction.followup.send("❌ Invalid region.", ephemeral=True)
            return

        data = await _state()
        attacker_profile = ensure_player_profile(data, str(interaction.user.id), interaction.user.display_name)
        attacker_th = int(attacker_profile.get("town_hall", 1) or 1)
        attacker_hero_power = get_total_hero_power(attacker_profile)
        # Equipped gear adds a power score (scaled ×0.5) on top of TH + heroes,
        # so a well-geared player conquers fortified regions more reliably.
        attacker_gear_power = calculate_power(get_effective_profile_stats(attacker_profile)) * 0.5
        attacker_power = _ATTACKER_BASE_POWER + attacker_th * 5 + attacker_hero_power * 4 + attacker_gear_power

        # Defender power is based on the region's existing conquest points
        # (representing fortification) plus a fixed baseline.
        territories = data.get("territories", {})
        region_data = territories.get(region_id, {})
        defender_conquest_pts = int(region_data.get("conquest_points", 0) or 0)
        defender_power = _DEFENDER_BASE_POWER + min(defender_conquest_pts // 50, 60)

        result = resolve_conquest(attacker_power=attacker_power, defender_power=defender_power)

        if result["attacker_won"]:
            clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

            def _update(state):
                territories = state.setdefault("territories", {})
                claim_region(territories, region_id, clan_name)
                add_conquest_points(territories, clan_name, 250)
                return state

            await update_mmo_state(ctx, _update)

        outcome = "Victory" if result["attacker_won"] else "Defeat"

        await interaction.followup.send(
            f"⚔️ Territory Battle Result: **{outcome}**\n"
            f"Your Power: **{int(attacker_power)}** (TH{attacker_th} + {attacker_hero_power} Hero Levels + {int(attacker_gear_power)} Gear)\n"
            f"Defense Power: **{defender_power}**\n"
            f"Attack Roll: {result['attack_roll']} | Defense Roll: {result['defense_roll']}"
        )

    @bot.tree.command(name="territoryincome", description="Collect territory resource income")
    async def territoryincome(interaction: discord.Interaction):
        data = await _state()
        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"
        cooldown_key = f"territoryincome:{interaction.guild.id if interaction.guild else 'dm'}:{interaction.user.id}"
        now = int(ctx.now())

        territory_cooldowns = data.setdefault("territory_cooldowns", {})
        last_claim = int(territory_cooldowns.get(cooldown_key, 0) or 0)
        remaining = (6 * 60 * 60) - (now - last_claim)

        if remaining > 0:
            hours, rem = divmod(remaining, 3600)
            minutes, _ = divmod(rem, 60)
            await interaction.response.send_message(
                f"⏳ Territory income can be collected again in **{hours}h {minutes}m**.",
                ephemeral=True,
            )
            return

        income = collect_region_income(data["territories"], clan_name)

        if income > 0:
            def _grant(state):
                if not isinstance(state, dict):
                    state = {}

                # Territory income is CLAN income — it goes into the shared
                # clan bank, not the collecting player's personal wallet.
                territories = state.setdefault("territories", {})
                territories["bank_gold"] = int(territories.get("bank_gold", 0) or 0) + int(income)

                return state

            def _stamp_income_cd(state):
                if not isinstance(state, dict):
                    state = {}
                state.setdefault("territory_cooldowns", {})[cooldown_key] = now
                return state

            await update_mmo_state(ctx, _grant)
            await update_mmo_state(ctx, _stamp_income_cd)

        await interaction.response.send_message(f"💰 {clan_name} deposited **{income:,} Gold** into the clan bank from territories")

    @claimterritory.autocomplete("region_id")
    @attackterritory.autocomplete("region_id")
    async def territory_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()

        return [
            app_commands.Choice(name=data["name"], value=region_id)
            for region_id, data in TERRITORY_REGIONS.items()
            if current in region_id or current in data["name"].lower()
        ][:25]