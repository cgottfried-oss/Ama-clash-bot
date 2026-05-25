from __future__ import annotations

from .config import MATCHMAKING_CONFIG



def expected_score(player_rating: int, opponent_rating: int):
    return 1 / (1 + (10 ** ((opponent_rating - player_rating) / 400)))



def calculate_elo_delta(player_rating: int, opponent_rating: int, won: bool):
    expected = expected_score(player_rating, opponent_rating)
    actual = 1 if won else 0

    return round(
        MATCHMAKING_CONFIG["k_factor"] * (actual - expected)
    )