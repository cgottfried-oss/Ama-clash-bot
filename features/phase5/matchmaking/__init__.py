"""Phase 5-4 matchmaking, MMR, league, and Elo systems."""

from .config import MATCHMAKING_CONFIG
from .elo import expected_score, calculate_elo_delta
from .leagues import LEAGUES, league_for_rating, next_league_progress
from .queue import build_queue_entry, find_best_match
from .battle import resolve_match
from .service import queue_player, play_ranked_match
from .formatting import format_match_result, format_league_profile

__all__ = [
    "MATCHMAKING_CONFIG",
    "expected_score",
    "calculate_elo_delta",
    "LEAGUES",
    "league_for_rating",
    "next_league_progress",
    "build_queue_entry",
    "find_best_match",
    "resolve_match",
    "queue_player",
    "play_ranked_match",
    "format_match_result",
    "format_league_profile",
]
