from __future__ import annotations

import discord
from discord import app_commands

from features.phase5.territory import (
    TERRITORY_REGIONS,
    add_conquest_points,
    claim_region,
    collect_region_income,
    format_territory_map,
    resolve_conquest,
)


PHASE5_TERRITORY_FILE = "/app/data/phase5_territories.json"



def register_economy_phase5_5_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _state():
        data = await safe_load_json(PHASE5_TERRITORY_FILE)

        if not isinstance(data, dict):
            data = {}

        data.setdefault("territories", {})
        return data

    @bot.tree.command(name="territorymap", description="View the clan territory map")
    async def territorymap(interaction: discord.Interaction):
        data = await _state()

        embed = discord.Embed(
            title="🗺️ Clan Territory Map",
            description=format_territory_map(data),
            color=0x2ECC71,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="claimterritory", description="Claim a territory region")
    @app_commands.describe(region_id="Territory region")
    async def claimterritory(interaction: discord.Interaction, region_id: str):
        region_id = region_id.strip().lower()

        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message(
                "❌ Invalid region.",
                ephemeral=True,
            )
            return

        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

        def _update(state):
            claim_region(state, region_id, clan_name)
            add_conquest_points(state, clan_name, 100)
            return state

        await update_json_file(PHASE5_TERRITORY_FILE, _update)

        await interaction.response.send_message(
            f"🏴 {clan_name} claimed {TERRITORY_REGIONS[region_id]['name']}"
        )

    @bot.tree.command(name="attackterritory", description="Attack a territory region")
    @app_commands.describe(region_id="Territory region")
    async def attackterritory(interaction: discord.Interaction, region_id: str):
        region_id = region_id.strip().lower()

        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message(
                "❌ Invalid region.",
                ephemeral=True,
            )
            return

        result = resolve_conquest(
            attacker_power=120,
            defender_power=100,
        )

        if result["attacker_won"]:
            clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

            def _update(state):
                claim_region(state, region_id, clan_name)
                add_conquest_points(state, clan_name, 250)
                return state

            await update_json_file(PHASE5_TERRITORY_FILE, _update)

        outcome = "Victory" if result["attacker_won"] else "Defeat"

        await interaction.response.send_message(
            f"⚔️ Territory Battle Result: **{outcome}**\n"
            f"Attack Roll: {result['attack_roll']}\n"
            f"Defense Roll: {result['defense_roll']}"
        )

    @bot.tree.command(name="territoryincome", description="Collect territory resource income")
    async def territoryincome(interaction: discord.Interaction):
        data = await _state()

        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"

        income = collect_region_income(data, clan_name)

        await interaction.response.send_message(
            f"💰 {clan_name} collected **{income:,} Gold** from territories"
        )

    @claimterritory.autocomplete("region_id")
    @attackterritory.autocomplete("region_id")
    async def territory_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()

        return [
            app_commands.Choice(
                name=data["name"],
                value=region_id,
            )
            for region_id, data in TERRITORY_REGIONS.items()
            if current in region_id or current in data["name"].lower()
        ][:25]
