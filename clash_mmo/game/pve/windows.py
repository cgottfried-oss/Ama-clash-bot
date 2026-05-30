from __future__ import annotations

import time



def open_damage_window(duration_seconds: int = 300):
    return {
        "opened_at": int(time.time()),
        "duration": duration_seconds,
    }



def is_damage_window_open(window: dict | None):
    if not window:
        return False

    now = int(time.time())

    return now <= (window["opened_at"] + window["duration"])
