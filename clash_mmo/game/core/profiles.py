from __future__ import annotations

from .cosmetics import default_cosmetics
from .inventory import default_inventory
from .matchmaking import default_matchmaking_profile



def default_player_profile(user_id: str, name: str):
    return {
        "identity": {
            "user_id": user_id,
            "name": name,
            "created_at": None,
        },
        "progression": {
            "level": 1,
            "xp": 0,
            "prestige": 0,
        },
        "stats": {
            "attack": 10,
            "defense": 10,
            "health": 100,
            "speed": 10,
            "crit": 0.05,
        },
        "inventory": default_inventory(),
        "cosmetics": default_cosmetics(),
        "matchmaking": default_matchmaking_profile(),
        "heroes": {},
        "territories": {},
        "season_data": {},
        "flags": {},
    }



def ensure_player_profile(container: dict, user_id: str, name: str):
    container.setdefault("players", {})

    if user_id not in container["players"]:
        container["players"][user_id] = default_player_profile(user_id, name)

    container["players"][user_id]["identity"]["name"] = name

    return container["players"][user_id]
