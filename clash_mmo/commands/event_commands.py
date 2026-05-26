from __future__ import annotations

import random
import time
import uuid

import discord

from clash_mmo.game.state import load_mmo_state, update_mmo_state


EVENT_TEMPLATES = [
    {
        "title": "Goblin Supply Raid",
        "description": "Goblin scouts found an exposed storage cart. Resolve it before the trail goes cold.",
        "reward": "Gold and season XP",
    },
    {
        "title": "Dark Elixir Surge",
        "description": "A strange dark elixir surge is boosting raid activity across the village.",
        "reward": "Dark elixir and bonus gold",
    },
    {
        "title": "Trader Caravan",
        "description": "A temporary trader caravan has entered clan territory with limited supplies.",
        "reward": "Random shop item or gold",
    },
]


def _now() -> int:
    return int(time.time())


def create_ai_event(state: dict) -> dict:
    template = random.choice(EVENT_TEMPLATES)
    event = {
        "id": uuid.uuid4().hex[:8],
        "title": template["title"],
        "description": template["description"],
        "reward": template["reward"],
        "created_at": _now(),
        "expires_at": _now() + 24 * 60 * 60,
        "resolved": False,
    }
    state.setdefault("events", []).append(event)
    state["events"] = state["events"][-25:]
    return event


def get_active_events(state: dict) -> list[dict]:
    return [
        event for event in state.get("events", [])
        if not event.get("resolved") and int(event.get("expires_at", 0) or 0) > _now()
    ]


def format_event_card(event: dict | None) -> str:
    if not event:
        return "No event generated."
    return (
        f"**ID:** `{event.get('id', 'unknown')}`\n"
        f"**Description:** {event.get('description', 'No description.')}\n"
        f"**Reward:** {event.get('reward', 'Unknown')}"
    )


def format_event_list(events: list[dict]) -> str:
    return "\n\n".join(
        f"**{event.get('title', 'World Event')}** — `{event.get('id', 'unknown')}`\n{event.get('description', 'No description.')}"
        for event in events
    )


def resolve_ai_event(state: dict, event_id: str) -> dict:
    event_id = event_id.strip().lower()
    for event in state.get("events", []):
        if str(event.get("id", "")).lower() == event_id:
            if event.get("resolved"):
                return {"ok": False, "error": "That event is already resolved."}
            event["resolved"] = True
            event["resolved_at"] = _now()
            return {"ok": True, "event": event}
    return {"ok": False, "error": "Event not found."}


def register_event_commands(bot, ctx):
    async def _state():
        data = await load_mmo_state(ctx)
        events = data.setdefault("events", {})
        events.setdefault("events", [])
        return events

    @bot.tree.command(name="generateevent", description="Generate a world event")
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
            title="World Event",
            description=format_event_card(event),
            color=0x8E44AD,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="worldevents", description="View active world events")
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

    @bot.tree.command(name="resolveevent", description="Resolve a world event")
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
