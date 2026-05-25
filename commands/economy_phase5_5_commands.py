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

    @bot.tree.command(name="p5territorymap", description="View the Phase 5 clan territory map")
    async def p5territorymap(interaction: discord.Interaction):
        data = await _state()
        embed = discord.Embed(title="🗺️ Phase 5 Clan Territory Map", description=format_territory_map(data), color=0x2ECC71)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="p5claimterritory", description="Claim a Phase 5 territory region")
    @app_commands.describe(region_id="Territory region")
    async def p5claimterritory(interaction: discord.Interaction, region_id: str):
        region_id = region_id.strip().lower()
        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message("❌ Invalid region.", ephemeral=True)
            return
        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"
        def _update(state):
            if not isinstance(state, dict):
                state = {}
            claim_region(state, region_id, clan_name)
            add_conquest_points(state, clan_name, 100)
            return state
        await update_json_file(PHASE5_TERRITORY_FILE, _update)
        await interaction.response.send_message(f"🏴 {clan_name} claimed {TERRITORY_REGIONS[region_id]['name']}")

    @bot.tree.command(name="p5attackterritory", description="Attack a Phase 5 territory region")
    @app_commands.describe(region_id="Territory region")
    async def p5attackterritory(interaction: discord.Interaction, region_id: str):
        region_id = region_id.strip().lower()
        if region_id not in TERRITORY_REGIONS:
            await interaction.response.send_message("❌ Invalid region.", ephemeral=True)
            return
        result = resolve_conquest(attacker_power=120, defender_power=100)
        if result["attacker_won"]:
            clan_name = interaction.guild.name if interaction.guild else "Solo Clan"
            def _update(state):
                if not isinstance(state, dict):
                    state = {}
                claim_region(state, region_id, clan_name)
                add_conquest_points(state, clan_name, 250)
                return state
            await update_json_file(PHASE5_TERRITORY_FILE, _update)
        outcome = "Victory" if result["attacker_won"] else "Defeat"
        await interaction.response.send_message(f"⚔️ Phase 5 Territory Battle Result: **{outcome}**\nAttack Roll: {result['attack_roll']}\nDefense Roll: {result['defense_roll']}")

    @bot.tree.command(name="p5territoryincome", description="Collect Phase 5 territory resource income")
    async def p5territoryincome(interaction: discord.Interaction):
        data = await _state()
        clan_name = interaction.guild.name if interaction.guild else "Solo Clan"
        income = collect_region_income(data, clan_name)
        await interaction.response.send_message(f"💰 {clan_name} collected **{income:,} Gold** from Phase 5 territories")

    @p5claimterritory.autocomplete("region_id")
    @p5attackterritory.autocomplete("region_id")
    async def territory_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=data["name"], value=region_id)
            for region_id, data in TERRITORY_REGIONS.items()
            if current in region_id or current in data["name"].lower()
        ][:25]
