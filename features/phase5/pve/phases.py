from __future__ import annotations



def get_boss_phase(raid: dict):
    health = float(raid.get("health", 0))
    max_health = float(raid.get("max_health", 1))

    ratio = health / max_health

    if ratio > 0.75:
        return 1

    if ratio > 0.5:
        return 2

    if ratio > 0.25:
        return 3

    return 4
