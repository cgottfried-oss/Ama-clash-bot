from __future__ import annotations

import random
import time
from datetime import datetime, timezone

from clash_mmo.game.state import load_mmo_state, update_mmo_state


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
    1: {"gold": 500, "elixir": 100},
    2: {"gold": 750, "shiny_ore": {"chance": 0.20, "min": 1, "max": 2}},
    3: {"gems": 25, "dark_elixir": {"chance": 0.10, "min": 10, "max": 30}},
    4: {"gold": 1200, "elixir": 250},
    5: {"title": "Season Grinder", "glowy_ore": {"chance": 0.08, "min": 1, "max": 1}},
    6: {"gold": 1800, "dark_elixir": {"chance": 0.15, "min": 20, "max": 60}},
    7: {"gems": 50, "shiny_ore": {"chance": 0.30, "min": 2, "max": 5}},
    8: {"gold": 2500, "elixir": 500, "glowy_ore": {"chance": 0.12, "min": 1, "max": 2}},
    9: {"medals": 20, "starry_ore": {"chance": 0.03, "min": 1, "max": 1}},
    10: {"border": "S1_BORDER", "starry_ore": {"chance": 0.05, "min": 1, "max": 1}},
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


def _ensure_season_state(data: dict) -> dict:
    seasons = data.setdefault("seasons", {})
    seasons.setdefault("current_season", current_season_key())
    seasons.setdefault("seasons", {})
    seasons.setdefault("global", {"last_reset": current_day_key()})
    seasons.setdefault("global", {}).setdefault("last_reset", current_day_key())
    return seasons


def _ensure_season_user(seasons: dict, season: str, user_id: str, name: str) -> dict:
    season_block = seasons.setdefault("seasons", {}).setdefault(season, {})
    users = season_block.setdefault("users", {})
    entry = users.setdefault(user_id, {
        "name": name,
        "season_xp": 0,
        "battle_pass_tier": 1,
        "claimed_tiers": [],
        "rating": 1000,
        "wins": 0,
        "losses": 0,
        "last_match_day": None,
    })
    entry["name"] = name
    entry.setdefault("season_xp", 0)
    entry.setdefault("battle_pass_tier", 1)
    entry.setdefault("claimed_tiers", [])
    entry.setdefault("rating", 1000)
    entry.setdefault("wins", 0)
    entry.setdefault("losses", 0)
    entry.setdefault("last_match_day", None)
    return entry


async def load_state(ctx):
    data = await load_mmo_state(ctx)
    return _ensure_season_state(data)


async def ensure_player(ctx, user_id: str, name: str):
    season = current_season_key()

    def _update(data):
        seasons = _ensure_season_state(data)
        _ensure_season_user(seasons, season, user_id, name)
        return data

    await update_mmo_state(ctx, _update)


async def add_season_xp(ctx, user_id: str, amount: int, name: str):
    season = current_season_key()
    unlocked = []

    def _update(data):
        seasons = _ensure_season_state(data)
        entry = _ensure_season_user(seasons, season, user_id, name)

        entry["season_xp"] = int(entry.get("season_xp", 0) or 0) + int(amount)

        while entry["season_xp"] >= xp_for_next_tier(int(entry.get("battle_pass_tier", 1) or 1)):
            cost = xp_for_next_tier(int(entry.get("battle_pass_tier", 1) or 1))
            entry["season_xp"] -= cost
            entry["battle_pass_tier"] += 1
            unlocked.append(entry["battle_pass_tier"])

        return data

    await update_mmo_state(ctx, _update)
    return unlocked


async def update_rating(ctx, user_id: str, won: bool, name: str):
    season = current_season_key()

    def _update(data):
        seasons = _ensure_season_state(data)
        entry = _ensure_season_user(seasons, season, user_id, name)

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

    await update_mmo_state(ctx, _update)


async def get_leaderboard(ctx, limit: int = 10):
    data = await load_state(ctx)
    season = current_season_key()

    users = data.get("seasons", {}).get("seasons", {}).get(season, {}).get("users", {})

    ranked = sorted(
        users.items(),
        key=lambda item: int(item[1].get("rating", 0) or 0),
        reverse=True,
    )

    return ranked[:limit]


def get_battle_pass_progress(entry: dict) -> dict:
    """Return player-facing battle pass progress data."""
    tier = int(entry.get("battle_pass_tier", 1) or 1)
    xp = int(entry.get("season_xp", 0) or 0)
    needed = xp_for_next_tier(tier)
    claimed = set(entry.get("claimed_tiers", []) or [])
    claimable = sorted(t for t in BATTLE_PASS_REWARDS if t <= tier and t not in claimed)
    return {
        "tier": tier,
        "season_xp": xp,
        "xp_needed": needed,
        "claimed_tiers": sorted(claimed),
        "claimable_tiers": claimable,
    }


def format_battle_pass_reward(reward: dict) -> str:
    labels = []
    for key, value in (reward or {}).items():
        if isinstance(value, dict) and "chance" in value:
            labels.append(_format_chance_reward(key, value))
            continue

        if key == "gold" and int(value or 0):
            labels.append(f"{int(value):,} Gold")
        elif key == "elixir" and int(value or 0):
            labels.append(f"{int(value):,} Elixir")
        elif key == "dark_elixir" and int(value or 0):
            labels.append(f"{int(value):,} Dark Elixir")
        elif key == "gems" and int(value or 0):
            labels.append(f"{int(value):,} Gems")
        elif key == "medals" and int(value or 0):
            labels.append(f"{int(value):,} Raid Medals")
        elif key == "raid_medals" and int(value or 0):
            labels.append(f"{int(value):,} Raid Medals")
        elif key in {"shiny_ore", "glowy_ore", "starry_ore"} and int(value or 0):
            labels.append(f"{int(value):,} {key.replace('_', ' ').title()}")
        elif key == "title" and value:
            labels.append(f"Title: {value}")
        elif key == "border" and value:
            labels.append(f"Border: {value}")

    return ", ".join(labels) or "Mystery Reward"


def roll_battle_pass_reward(reward: dict) -> dict:
    """Resolve guaranteed rewards and chance-based rewards for a pass tier."""
    resolved = {}
    chance_details = {}

    for key, value in (reward or {}).items():
        if isinstance(value, dict) and "chance" in value:
            chance = float(value.get("chance", 0) or 0)
            minimum = int(value.get("min", 0) or 0)
            maximum = int(value.get("max", minimum) or minimum)
            if random.random() < chance:
                resolved[key] = random.randint(minimum, maximum)
            chance_details[key] = {
                "chance": chance,
                "min": minimum,
                "max": maximum,
                "awarded": resolved.get(key, 0),
            }
        else:
            resolved[key] = value

    return {
        "resolved": resolved,
        "chance_details": chance_details,
    }


def _format_chance_reward(key: str, value: dict) -> str:
    chance = float(value.get("chance", 0) or 0)
    minimum = int(value.get("min", 0) or 0)
    maximum = int(value.get("max", minimum) or minimum)
    pretty = key.replace("_", " ").title()
    amount = str(minimum) if minimum == maximum else f"{minimum}-{maximum}"
    return f"{chance * 100:.0f}% chance: {amount} {pretty}"
