from __future__ import annotations

from .config import MATCHMAKING_CONFIG



def build_queue_entry(user_id: str, rating: int, region: str = "global"):
    return {
        "user_id": user_id,
        "rating": rating,
        "region": region,
    }



def find_best_match(queue: list[dict], entry: dict):
    closest = None
    closest_gap = None

    for other in queue:
        if other["user_id"] == entry["user_id"]:
            continue

        gap = abs(other["rating"] - entry["rating"])

        if gap > MATCHMAKING_CONFIG["search_range"]:
            continue

        if closest_gap is None or gap < closest_gap:
            closest = other
            closest_gap = gap

    return closest