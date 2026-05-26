from __future__ import annotations

import time



def should_spawn_event(state: dict, cooldown_seconds: int = 3600):
    last_spawn = int(state.get("last_spawn", 0))

    return int(time.time()) >= (last_spawn + cooldown_seconds)



def mark_event_spawned(state: dict):
    state["last_spawn"] = int(time.time())
    return state