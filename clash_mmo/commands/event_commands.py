from __future__ import annotations

import random

import discord

from clash_mmo.game.pve.world_events import (
    WORLD_EVENTS,
    event_keys,
    get_active_event,
    get_event_config,
    start_event,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state


# These commands previously drove a separate, decorative ai_events system whose
# effects were never read by gameplay. They now drive the real world_events
# system (the same one /startevent, /eventstatus and the auto-rotation loop use),
# so a single source of truth powers every event surface.

def register_event_commands(bot, ctx):

    @bot.tree.command(name="generateevent", description="Generate a random world event")
    async def generateevent(interaction: discord.Interaction):
        data = await load_mmo_state(ctx)
        if get_active_event(data) is not None:
            active = get_active_event(data)
            cfg = get_event_config(active.get("key")) or {}
            await interaction.response.send_message(
                f"⚠️ An event is already active: **{cfg.get('name', active.get('key'))}**. "
                f"Use `/worldevents` to view it.",
                ephemeral=True,
            )
            return

        key = random.choice(event_keys())

        def _update(state):
            start_event(state, key)
            return state

        await update_mmo_state(ctx, _update)

        cfg = get_event_config(key) or {}
        embed = discord.Embed(
            title=f"🎉 {cfg.get('name', key)} has begun!",
            description=f"{cfg.get('description', '')}\nActive for **24 hours**.",
            color=0x8E44AD,
        )
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="worldevents", description="View the active world event")
    async def worldevents(interaction: discord.Interaction):
        data = await load_mmo_state(ctx)
        active = get_active_event(data)

        if not active:
            await interaction.response.send_message(
                "No active world events right now. One may roll in automatically, "
                "or a leader can trigger one with `/startevent`.",
                ephemeral=True,
            )
            return

        cfg = get_event_config(active.get("key")) or {}
        embed = discord.Embed(
            title="🌍 Active World Event",
            description=f"**{cfg.get('name', active.get('key'))}**\n{cfg.get('description', '')}",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed)
