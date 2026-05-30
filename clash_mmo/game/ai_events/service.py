from __future__ import annotations

from .effects import apply_event_effect, resolve_event_effect
from .generator import generate_world_event
from .scheduler import mark_event_spawned



def create_ai_event(state: dict):
    event = generate_world_event()

    state.setdefault("events", [])
    state["events"].append(event)

    apply_event_effect(state, event)
    mark_event_spawned(state)

    return event



def get_active_events(state: dict):
    return [
        event
        for event in state.get("events", [])
        if event.get("active")
    ]



def resolve_ai_event(state: dict, event_id: str):
    for event in state.get("events", []):
        if event["event_id"] != event_id:
            continue

        resolve_event_effect(event)

        return {
            "ok": True,
            "event": event,
        }

    return {
        "ok": False,
        "error": "Event not found.",
    }