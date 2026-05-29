from __future__ import annotations

import discord
from discord import app_commands
from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.state import load_mmo_state, update_mmo_state
from clash_mmo.game.territory import (
    TERRITORY_REGIONS,
    add_conquest_points,
    claim_region,
    collect_region_income,
    format_territory_map,
    resolve_conquest,
)


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
        region_id = region_id.strip().lower()

        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message("❌ Invalid region.", ephemeral=True)
            return

        result = resolve_conquest(attacker_power=120, defender_power=100)

        if result["attacker_won"]:
            clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

            def _update(state):
                territories = state.setdefault("territories", {})
                claim_region(territories, region_id, clan_name)
                add_conquest_points(territories, clan_name, 250)
                return state

            await update_mmo_state(ctx, _update)

        outcome = "Victory" if result["attacker_won"] else "Defeat"

        await interaction.response.send_message(
            f"⚔️ Territory Battle Result: **{outcome}**\nAttack Roll: {result['attack_roll']}\nDefense Roll: {result['defense_roll']}"
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
            
                profile = ensure_player_profile(
                    state,
                    str(interaction.user.id),
                    interaction.user.display_name,
                )
            
                profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + int(income))
            
                stats = profile.setdefault("stats", {})
                stats["lifetime_gold"] = int(stats.get("lifetime_gold", 0) or 0) + int(income)
            
                identity = profile.setdefault("identity", {})
                identity["display_name"] = interaction.user.display_name
                profile["name"] = interaction.user.display_name
            
                return state
            
            def _stamp_income_cd(state):
                if not isinstance(state, dict):
                    state = {}
                state.setdefault("territory_cooldowns", {})[cooldown_key] = now
                return state

            await update_mmo_state(ctx, _grant)
            await update_mmo_state(ctx, _stamp_income_cd)

        await interaction.response.send_message(f"💰 {clan_name} collected **{income:,} Gold** from territories")

    @claimterritory.autocomplete("region_id")
    @attackterritory.autocomplete("region_id")
    async def territory_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()

        return [
            app_commands.Choice(name=data["name"], value=region_id)
            for region_id, data in TERRITORY_REGIONS.items()
            if current in region_id or current in data["name"].lower()
        ][:25]
