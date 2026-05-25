from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path

SEASON_FILE_NAME = "phase5_seasons.json"

LEAGUES = [
    (0, "Bronze"),
    (1000, "Silver"),
    (2000, "Gold"),
    (3200, "Crystal"),
    (4500, "Master"),
    (6000, "Champion"),
    (8000, "Titan"),
    (10000, "Legend"),
]

BATTLE_PASS_REWARDS = {
    1: {"gold": 500},
    2: {"gold": 750},
    3: {"gems": 25},
    4: {"gold": 1200},
    5: {"title": "Season Grinder"},
    6: {"gold": 1800},
    7: {"gems": 50},
    8: {"gold": 2500},
    9: {"medals": 20},
    10: {"border": "S1_BORDER"},
}


def now_ts() -> int:
    return int(time.time())


def current_season_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def current_day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def xp_for_next_tier(tier: int) -> int:
    return 100 + ((tier - 1) * 50)


def get_league_name(rating: int) -> str:
    current = "Bronze"
    for threshold, name in LEAGUES:
        if rating >= threshold:
            current = name
    return current


def default_state():
    return {
        "current_season": current_season_key(),
        "seasons": {},
        "global": {
            "last_reset": current_day_key(),
        },
    }


async def load_state(ctx):
    season_file = str(Path(ctx.DATA_DIR) / SEASON_FILE_NAME)
    data = await ctx.safe_load_json(season_file)

    if not isinstance(data, dict):
        data = {}

    base = default_state()
    for k, v in base.items():
        data.setdefault(k, v)

    return data


async def ensure_player(ctx, user_id: str, name: str):
    season = current_season_key()

    def _update(data):
        if not isinstance(data, dict):
            data = default_state()

        data.setdefault("seasons", {})
        season_block = data["seasons"].setdefault(season, {})
        users = season_block.setdefault("users", {})

        users.setdefault(user_id, {
            "name": name,
            "season_xp": 0,
            "battle_pass_tier": 1,
            "claimed_tiers": [],
            "rating": 1000,
            "wins": 0,
            "losses": 0,
            "last_match_day": None,
        })

        users[user_id]["name"] = name
        return data

    await ctx.update_json_file(str(Path(ctx.DATA_DIR) / SEASON_FILE_NAME), _update)


async def add_season_xp(ctx, user_id: str, amount: int, name: str):
    season = current_season_key()
    unlocked = []

    def _update(data):
        data.setdefault("seasons", {})
        season_block = data["seasons"].setdefault(season, {})
        users = season_block.setdefault("users", {})

        entry = users.setdefault(user_id, {
            "name": name,
            "season_xp": 0,
            "battle_pass_tier": 1,
            "claimed_tiers": [],
            "rating": 1000,
            "wins": 0,
            "losses": 0,
        })

        entry["season_xp"] = int(entry.get("season_xp", 0) or 0) + int(amount)

        while entry["season_xp"] >= xp_for_next_tier(int(entry.get("battle_pass_tier", 1) or 1)):
            cost = xp_for_next_tier(int(entry.get("battle_pass_tier", 1) or 1))
            entry["season_xp"] -= cost
            entry["battle_pass_tier"] += 1
            unlocked.append(entry["battle_pass_tier"])

        return data

    await ctx.update_json_file(str(Path(ctx.DATA_DIR) / SEASON_FILE_NAME), _update)
    return unlocked


async def update_rating(ctx, user_id: str, won: bool, name: str):
    season = current_season_key()

    def _update(data):
        data.setdefault("seasons", {})
        season_block = data["seasons"].setdefault(season, {})
        users = season_block.setdefault("users", {})

        entry = users.setdefault(user_id, {
            "name": name,
            "season_xp": 0,
            "battle_pass_tier": 1,
            "claimed_tiers": [],
            "rating": 1000,
            "wins": 0,
            "losses": 0,
        })

        rating = int(entry.get("rating", 1000) or 1000)

        if won:
            rating += random.randint(24, 38)
            entry["wins"] = int(entry.get("wins", 0) or 0) + 1
        else:
            rating -= random.randint(12, 25)
            entry["losses"] = int(entry.get("losses", 0) or 0) + 1

        entry["rating"] = max(0, rating)
        entry["name"] = name

        return data

    await ctx.update_json_file(str(Path(ctx.DATA_DIR) / SEASON_FILE_NAME), _update)


async def get_leaderboard(ctx, limit: int = 10):
    data = await load_state(ctx)
    season = current_season_key()

    users = data.get("seasons", {}).get(season, {}).get("users", {})

    ranked = sorted(
        users.items(),
        key=lambda item: int(item[1].get("rating", 0) or 0),
        reverse=True,
    )

    return ranked[:limit]
