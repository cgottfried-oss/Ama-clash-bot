from __future__ import annotations

from .leagues import league_for_rating



def format_match_result(result: dict):
    outcome = "Victory" if result["player_won"] else "Defeat"

    return (
        f"⚔️ {outcome}\n"
        f"MMR Change: {result['player_delta']:+}\n"
        f"Power: {result['result']['player_power']} vs "
        f"{result['result']['opponent_power']}"
    )



def format_league_profile(profile: dict):
    matchmaking = profile.get("matchmaking", {})
    rating = int(matchmaking.get("rating", 1000) or 1000)

    return (
        f"🏆 League: {league_for_rating(rating)}\n"
        f"📈 Rating: {rating:,}"
    )