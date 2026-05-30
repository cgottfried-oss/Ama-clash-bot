from __future__ import annotations

import random



def default_matchmaking_profile():
    return {
        "rating": 1000,
        "wins": 0,
        "losses": 0,
        "streak": 0,
        "highest_rating": 1000,
        "queue_data": {
            "last_queue_at": None,
            "region": "global",
        },
    }



def apply_match_result(profile: dict, won: bool):
    rating = int(profile.get("rating", 1000) or 1000)

    if won:
        delta = random.randint(24, 38)
        profile["wins"] = int(profile.get("wins", 0) or 0) + 1
        profile["streak"] = max(1, int(profile.get("streak", 0) or 0) + 1)
    else:
        delta = -random.randint(12, 24)
        profile["losses"] = int(profile.get("losses", 0) or 0) + 1
        profile["streak"] = min(-1, int(profile.get("streak", 0) or 0) - 1)

    rating += delta
    rating = max(0, rating)

    profile["rating"] = rating
    profile["highest_rating"] = max(
        int(profile.get("highest_rating", 1000) or 1000),
        rating,
    )

    return profile