from __future__ import annotations


def player_power(profile: dict) -> int:
    town_hall = int(profile.get("town_hall", 1) or 1)
    clan_xp = int(profile.get("clan_xp", 0) or 0)
    gold = int(profile.get("gold", 0) or 0)
    return town_hall * 100 + min(clan_xp, 5000) // 10 + min(gold, 100000) // 1000


def match_score(attacker: dict, defender: dict) -> int:
    return abs(player_power(attacker) - player_power(defender))


def sort_match_candidates(attacker: dict, candidates: list[dict]) -> list[dict]:
    return sorted(candidates, key=lambda candidate: match_score(attacker, candidate))
