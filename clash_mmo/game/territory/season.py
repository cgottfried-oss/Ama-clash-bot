from __future__ import annotations

import time

from clash_mmo.game.territory.regions import TERRITORY_REGIONS


TERRITORY_SEASON_SECONDS = 14 * 24 * 60 * 60


def current_territory_season(now: int | None = None) -> str:
    now = int(now or time.time())
    season_index = now // TERRITORY_SEASON_SECONDS
    return f"territory-season-{season_index}"


def ensure_territory_state(state: dict, now: int | None = None) -> dict:
    territories = state.setdefault("territories", {})
    if not isinstance(territories, dict):
        territories = {}
        state["territories"] = territories

    season_key = current_territory_season(now)
    territories.setdefault("season", season_key)
    territories.setdefault("regions", {})
    territories.setdefault("history", [])

    if territories.get("season") != season_key:
        territories["season"] = season_key
        territories["regions"] = {}
        territories.setdefault("history", []).append({"at": int(now or time.time()), "event": "season_reset", "season": season_key})

    for region_id in TERRITORY_REGIONS:
        territories["regions"].setdefault(region_id, {"owner_clan": None, "claimed_by": None, "claimed_at": None, "defense_power": 0})

    return territories


def get_region_state(state: dict, region_id: str, now: int | None = None) -> dict:
    territories = ensure_territory_state(state, now)
    return territories.setdefault("regions", {}).setdefault(region_id, {"owner_clan": None, "claimed_by": None, "claimed_at": None, "defense_power": 0})
