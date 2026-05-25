from __future__ import annotations

from .bosses import RAID_BOSSES



def create_raid_instance(boss_id: str):
    boss = RAID_BOSSES[boss_id]

    return {
        "boss_id": boss_id,
        "boss_name": boss["name"],
        "health": boss["max_health"],
        "max_health": boss["max_health"],
        "players": [],
        "damage": {},
        "active": True,
    }



def get_active_raid(state: dict):
    return state.get("active_raid")



def close_raid(state: dict):
    state["active_raid"] = None
    return state
