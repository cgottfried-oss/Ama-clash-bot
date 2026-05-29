from __future__ import annotations

import time

from clash_mmo.game.ai_events.generator import generate_ai_event
from clash_mmo.game.ai_events.scheduler import schedule_next_event


def ensure_event_state(state: dict) -> dict:
    event_state = state.setdefault("events", {})
    if not isinstance(event_state, dict):
        event_state = {"events": []}
        state["events"] = event_state
    event_state.setdefault("events", [])
    event_state.setdefault("next_event_at", 0)
    return event_state


def get_active_events(state: dict, now: int | None = None) -> list[dict]:
    now = int(now or time.time())
    event_state = ensure_event_state(state)
    return [
        event
        for event in event_state.setdefault("events", [])
        if event.get("status") == "active" and int(event.get("ends_at", 0) or 0) > now
    ]


def maybe_generate_event(state: dict, now: int | None = None) -> dict | None:
    now = int(now or time.time())
    event_state = ensure_event_state(state)
    if int(event_state.get("next_event_at", 0) or 0) > now:
        return None
    event = generate_ai_event(now=now)
    event_state.setdefault("events", []).append(event)
    schedule_next_event(state, now=now)
    return event


def resolve_event(state: dict, event_id: str, now: int | None = None) -> tuple[bool, dict | None]:
    now = int(now or time.time())
    event_state = ensure_event_state(state)
    for event in event_state.setdefault("events", []):
        if event.get("event_id") != event_id:
            continue
        if event.get("status") != "active":
            return False, event
        event["status"] = "resolved"
        event["resolved_at"] = now
        return True, event
    return False, None
