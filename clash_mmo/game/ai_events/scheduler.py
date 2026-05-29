from __future__ import annotations

import time


DEFAULT_EVENT_INTERVAL_SECONDS = 6 * 60 * 60


def schedule_next_event(state: dict, now: int | None = None, interval_seconds: int = DEFAULT_EVENT_INTERVAL_SECONDS) -> int:
    now = int(now or time.time())
    event_state = state.setdefault("events", {})
    next_at = now + int(interval_seconds or DEFAULT_EVENT_INTERVAL_SECONDS)
    event_state["next_event_at"] = next_at
    return next_at
