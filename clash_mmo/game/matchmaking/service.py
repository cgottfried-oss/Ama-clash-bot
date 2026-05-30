from __future__ import annotations

import random

from .battle import resolve_match
from .elo import calculate_elo_delta
from .queue import build_queue_entry
from ..equipment.service import get_effective_profile_stats
from ..heroes import get_total_hero_power


GLOBAL_QUEUE = []

# Each hero level contributes this many points to matchmaking power.
# Keeps hero investment meaningful without completely overriding gear skill.
HERO_POWER_WEIGHT = 3.0



def queue_player(profile: dict, region: str = "global"):
    matchmaking = profile.setdefault("matchmaking", {})

    entry = build_queue_entry(
        user_id=profile["identity"]["user_id"],
        rating=int(matchmaking.get("rating", 1000) or 1000),
        region=region,
    )

    GLOBAL_QUEUE.append(entry)

    return entry



def _get_combat_power(profile: dict) -> dict:
    """Return effective stats boosted by total hero level power.

    Hero power is converted into a flat attack bonus so it integrates
    cleanly with the existing calculate_power() weighting in battle.py.
    """
    stats = get_effective_profile_stats(profile)
    hero_power = get_total_hero_power(profile)
    hero_attack_bonus = hero_power * HERO_POWER_WEIGHT

    boosted = dict(stats)
    boosted["attack"] = float(boosted.get("attack", 0)) + hero_attack_bonus
    boosted["_hero_power"] = hero_power  # surfaced in match result for display

    return boosted



def play_ranked_match(player_profile: dict, opponent_profile: dict):
    player_stats = _get_combat_power(player_profile)
    opponent_stats = _get_combat_power(opponent_profile)

    result = resolve_match(player_stats, opponent_stats)

    player_mm = player_profile.setdefault("matchmaking", {})
    opponent_mm = opponent_profile.setdefault("matchmaking", {})

    player_rating = int(player_mm.get("rating", 1000) or 1000)
    opponent_rating = int(opponent_mm.get("rating", 1000) or 1000)

    player_won = result["outcome"] == "player"

    player_delta = calculate_elo_delta(
        player_rating,
        opponent_rating,
        player_won,
    )

    opponent_delta = calculate_elo_delta(
        opponent_rating,
        player_rating,
        not player_won,
    )

    player_mm["rating"] = max(0, player_rating + player_delta)
    opponent_mm["rating"] = max(0, opponent_rating + opponent_delta)

    return {
        "player_won": player_won,
        "player_delta": player_delta,
        "opponent_delta": opponent_delta,
        "player_hero_power": player_stats.get("_hero_power", 0),
        "opponent_hero_power": opponent_stats.get("_hero_power", 0),
        "result": result,
    }
