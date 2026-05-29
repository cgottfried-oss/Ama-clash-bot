from __future__ import annotations

import time
from datetime import datetime, timezone


SEASON_SECONDS = 30 * 24 * 60 * 60


def current_season_key(now: int | None = None) -> str:
    now = int(now or time.time())
    dt = datetime.fromtimestamp(now, tz=timezone.utc)
    return dt.strftime("%Y-%m")


def ensure_season_state(data: dict, now: int | None = None) -> dict:
    seasons = data.setdefault("seasons", {})
    if not isinstance(seasons, dict):
        seasons = {}
        data["seasons"] = seasons

    season_key = current_season_key(now)
    seasons.setdefault("current", season_key)
    seasons.setdefault("seasons", {})
    seasons["seasons"].setdefault(season_key, {"users": {}, "started_at": int(now or time.time())})
    return seasons


def ensure_user_season(data: dict, user_id: str, now: int | None = None) -> dict:
    seasons = ensure_season_state(data, now)
    season_key = seasons.get("current") or current_season_key(now)
    season = seasons.setdefault("seasons", {}).setdefault(season_key, {"users": {}, "started_at": int(now or time.time())})
    users = season.setdefault("users", {})
    user = users.setdefault(str(user_id), {"xp": 0, "claimed_tiers": []})
    user.setdefault("xp", 0)
    user.setdefault("claimed_tiers", [])
    return user


def add_season_xp(data: dict, user_id: str, amount: int, now: int | None = None) -> dict:
    user = ensure_user_season(data, user_id, now)
    user["xp"] = max(0, int(user.get("xp", 0) or 0) + max(0, int(amount or 0)))
    return user


def battle_pass_tier_for_xp(xp: int) -> int:
    return min(50, max(0, int(xp or 0) // 250))


def available_battle_pass_tiers(user_season: dict) -> list[int]:
    tier = battle_pass_tier_for_xp(int(user_season.get("xp", 0) or 0))
    claimed = {int(t) for t in user_season.get("claimed_tiers", []) if str(t).isdigit()}
    return [t for t in range(1, tier + 1) if t not in claimed]
