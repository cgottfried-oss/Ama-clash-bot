from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.state import load_mmo_state, update_mmo_state
from clash_mmo.game.territory import (
    TERRITORY_REGIONS,
    add_conquest_points,
    claim_region,
    collect_region_income,
    format_territory_map,
    resolve_conquest,
)


def register_economy_commands(bot, ctx):

    async def _state():
        data = await load_mmo_state(ctx)
        data.setdefault("territories", {})
        return data

    @bot.tree.command(name="territorymap", description="View the clan territory map")
    async def territorymap(interaction: discord.Interaction):
        data = await _state()
        embed = discord.Embed(title="🗺️ Clan Territory Map", description=format_territory_map(data["territories"]), color=0x2ECC71)
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

        income = collect_region_income(data["territories"], clan_name)

        if income > 0:
            def _grant(stored):
                if not isinstance(stored, dict):
                    stored = {}

                users = stored.setdefault("users", {})
                entry = users.setdefault(str(interaction.user.id), {
                    "balance": 0,
                    "lifetime_earned": 0,
                    "name": interaction.user.display_name,
                })

                entry["balance"] = int(entry.get("balance", 0) or 0) + int(income)
                entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + int(income)
                entry["name"] = interaction.user.display_name

                return stored

            await ctx.update_json_file(ctx.COINS_FILE, _grant)

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