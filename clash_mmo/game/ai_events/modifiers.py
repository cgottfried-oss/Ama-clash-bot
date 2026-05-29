from __future__ import annotations

import time


def get_active_event_modifiers(state: dict, now: int | None = None) -> dict:
    now = int(now or time.time())
    event_state = state.setdefault("events", {})
    events = event_state.setdefault("events", [])
    modifiers = {}

    for event in events:
        if event.get("status") != "active":
            continue
        if int(event.get("ends_at", 0) or 0) <= now:
            continue
        effects = event.get("effects", {}) or {}
        for key, value in effects.items():
            modifiers[key] = int(modifiers.get(key, 0) or 0) + int(value or 0)

    return modifiers
