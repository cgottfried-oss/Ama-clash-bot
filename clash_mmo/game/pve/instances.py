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
        "defeated": False,
        "rewards_claimed": False,
    }



def get_active_raid(state: dict):
    raid = state.get("active_raid")

    if not raid:
        return None

    if not raid.get("active") or int(raid.get("health", 0) or 0) <= 0:
        return None

    return raid



def close_raid(state: dict):
    state["active_raid"] = None
    return state