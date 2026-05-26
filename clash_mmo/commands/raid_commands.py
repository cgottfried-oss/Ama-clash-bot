from __future__ import annotations

import discord
from discord import app_commands

from features.phase5.core.profiles import ensure_player_profile
from features.phase5.pve import (
    RAID_BOSSES,
    attack_raid_boss,
    format_attack_result,
    format_raid_status,
    get_active_raid,
    join_raid,
    start_raid,
)

from features.phase5.state import (
    ensure_mmo_player,
    load_mmo_state,
    update_mmo_state,
)


def register_economy_phase5_6_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _raid_state():
        data = await load_mmo_state(ctx)
        return data.setdefault("raids", {})

    async def _profiles():
        data = await load_mmo_state(ctx)
        data.setdefault("players", {})
        return data

    @bot.tree.command(name="startraid", description="Start a Phase 5 PvE raid boss")
    @app_commands.describe(boss_id="Raid boss ID")
    async def p5startraid(interaction: discord.Interaction, boss_id: str):
        boss_id = boss_id.strip().lower()
        if boss_id not in RAID_BOSSES:
            await interaction.response.send_message("Invalid boss.", ephemeral=True)
            return
        def _update(state):
            if not isinstance(state, dict):
                state = {}
            start_raid(state, boss_id)
            return state
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"Phase 5 raid started: {RAID_BOSSES[boss_id]['name']}")

    @bot.tree.command(name="raidstatus", description="View current Phase 5 raid status")
    async def p5raidstatus(interaction: discord.Interaction):
        state = await _raid_state()
        raid = get_active_raid(state)
        if not raid:
            await interaction.response.send_message("No active Phase 5 raid.", ephemeral=True)
            return
        embed = discord.Embed(title="Phase 5 PvE Raid", description=format_raid_status(raid), color=0xE74C3C)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="joinraid", description="Join the active Phase 5 raid")
    async def p5joinraid(interaction: discord.Interaction):
        joined = False
        def _update(state):
            nonlocal joined
            if not isinstance(state, dict):
                state = {}
            raid = get_active_raid(state)
            if raid:
                join_raid(raid, str(interaction.user.id))
                joined = True
            return state
        await update_mmo_state(ctx, _update)
        if not joined:
            await interaction.response.send_message("No active Phase 5 raid.", ephemeral=True)
            return
        await interaction.response.send_message("You joined the Phase 5 raid.")

    @bot.tree.command(name="attackraid", description="Attack the active Phase 5 raid boss")
    async def p5attackraid(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(profiles, str(interaction.user.id), interaction.user.display_name)
        state = await _raid_state()
        raid = get_active_raid(state)
        if not raid:
            await interaction.response.send_message("No active Phase 5 raid.", ephemeral=True)
            return
        result = attack_raid_boss(raid, profile)
        def _update(state_data):
            if not isinstance(state_data, dict):
                state_data = {}
            state_data["active_raid"] = raid
            return state_data
        await update_mmo_state(ctx, _update)
        embed = discord.Embed(title="Phase 5 Raid Attack", description=format_attack_result(result), color=0xF39C12)
        await interaction.response.send_message(embed=embed)

    @p5startraid.autocomplete("boss_id")
    async def boss_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=data["name"], value=boss_id)
            for boss_id, data in RAID_BOSSES.items()
            if current in boss_id or current in data["name"].lower()
        ][:25]