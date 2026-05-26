from __future__ import annotations

import discord

from clash_mmo.game.ai_events import (
    create_ai_event,
    format_event_card,
    format_event_list,
    get_active_events,
    resolve_ai_event,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state


def register_event_commands(bot, ctx):
    async def _state():
        data = await load_mmo_state(ctx)
        events = data.setdefault("events", {})
        events.setdefault("events", [])
        return events

    @bot.tree.command(name="generateevent", description="Generate an AI world event")
    async def generateevent(interaction: discord.Interaction):
        def _update(state):
            events = state.setdefault("events", {})
            event = create_ai_event(events)
            events["latest_event"] = event
            return state

        await update_mmo_state(ctx, _update)

        refreshed = await _state()
        event = refreshed.get("latest_event")

        embed = discord.Embed(
            title="AI World Event",
            description=format_event_card(event),
            color=0x8E44AD,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="worldevents", description="View active AI world events")
    async def worldevents(interaction: discord.Interaction):
        state = await _state()
        events = get_active_events(state)

        if not events:
            await interaction.response.send_message(
                "No active world events.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Active World Events",
            description=format_event_list(events),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="resolveevent", description="Resolve an AI world event")
    async def resolveevent(interaction: discord.Interaction, event_id: str):
        state = await _state()
        result = resolve_ai_event(state, event_id)

        if not result["ok"]:
            await interaction.response.send_message(
                result["error"],
                ephemeral=True,
            )
            return

        def _update(container):
            container.setdefault("events", {}).update(state)
            return container

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"✅ Resolved event: {result['event']['title']}"
        )
