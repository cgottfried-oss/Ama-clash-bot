#from __future__ import annotations

import random



def calculate_power(stats: dict):
    return (
        float(stats.get("attack", 0)) * 1.6 +
        float(stats.get("defense", 0)) * 1.2 +
        float(stats.get("health", 0)) * 0.15 +
        float(stats.get("speed", 0)) * 1.1 +
        float(stats.get("crit", 0)) * 100
    )



def resolve_match(player_stats: dict, opponent_stats: dict):
    player_power = calculate_power(player_stats)
    opponent_power = calculate_power(opponent_stats)

    player_roll = player_power * random.uniform(0.85, 1.15)
    opponent_roll = opponent_power * random.uniform(0.85, 1.15)

    outcome = "player"

    if opponent_roll > player_roll:
        outcome = "opponent"

    return {
        "player_power": round(player_power, 2),
        "opponent_power": round(opponent_power, 2),
        "outcome": outcome,
    }
