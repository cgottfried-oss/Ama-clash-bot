from __future__ import annotations

from .battle import resolve_match
from .elo import calculate_elo_delta
from .queue import build_queue_entry
from ..equipment.service import get_effective_profile_stats


GLOBAL_QUEUE = []



def queue_player(profile: dict, region: str = "global"):
    matchmaking = profile.setdefault("matchmaking", {})

    entry = build_queue_entry(
        user_id=profile["identity"]["user_id"],
        rating=int(matchmaking.get("rating", 1000) or 1000),
        region=region,
    )

    GLOBAL_QUEUE.append(entry)

    return entry



def play_ranked_match(player_profile: dict, opponent_profile: dict):
    player_stats = get_effective_profile_stats(player_profile)
    opponent_stats = get_effective_profile_stats(opponent_profile)

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
        "result": result,
    }