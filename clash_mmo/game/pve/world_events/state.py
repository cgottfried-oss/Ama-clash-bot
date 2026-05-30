from __future__ import annotations

import time

# World event active-state lives here. Kept at the same location the original
# pvp system used (state["pvp"]["events"]["active"]) so existing readers like
# /raiduser keep working without a data migration.

EVENT_DURATION = 24 * 60 * 60


def _now() -> int:
    return int(time.time())


def _events_bucket(state: dict) -> dict:
    pvp = state.setdefault("pvp", {})
    events = pvp.setdefault("events", {})
    return events


def get_active_event(state: dict) -> dict | None:
    """Return the active event dict, or None if none active / expired."""
    active = _events_bucket(state).get("active")
    if not active:
        return None
    if int(active.get("ends_at", 0) or 0) <= _now():
        return None
    return active


def get_active_event_key(state: dict) -> str | None:
    active = get_active_event(state)
    return active.get("key") if active else None


def start_event(state: dict, key: str) -> dict:
    """Set the given event key active for EVENT_DURATION. Returns the entry."""
    now = _now()
    entry = {
        "key": key,
        "started_at": now,
        "ends_at": now + EVENT_DURATION,
    }
    _events_bucket(state)["active"] = entry
    return entry
