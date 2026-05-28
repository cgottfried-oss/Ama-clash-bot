from __future__ import annotations

import random

from clash_mmo.game.equipment.service import get_effective_profile_stats
from clash_mmo.game.heroes import normalize_hero_loadouts


def calculate_raid_damage(profile: dict) -> dict:
    stats = get_effective_profile_stats(profile)

    town_hall = int(profile.get("town_hall", 1) or 1)
    attack = float(stats.get("attack", 0) or 0)
    crit = float(stats.get("crit", 0) or 0)

    heroes = normalize_hero_loadouts(profile)
    unlocked_heroes = [
        hero for hero in heroes.values()
        if hero and hero.get("unlocked", True)
    ]

    total_hero_levels = sum(int(hero.get("level", 1) or 1) for hero in unlocked_heroes)
    active_hero_id = profile.get("active_hero")
    active_hero = heroes.get(active_hero_id, {}) if active_hero_id else {}
    active_hero_level = int(active_hero.get("level", 1) or 1)

    th_power = town_hall * 325
    stat_power = attack * 85
    roster_hero_power = total_hero_levels * 55
    active_hero_power = active_hero_level * 90

    base_damage = th_power + stat_power + roster_hero_power + active_hero_power

    variance = random.uniform(0.85, 1.20)
    damage = int(base_damage * variance)

    crit_roll = random.random() < max(0.0, min(0.75, crit))
    if crit_roll:
        damage = int(damage * 1.5)

    return {
        "damage": max(1, damage),
        "base_damage": int(base_damage),
        "crit": crit_roll,
        "town_hall": town_hall,
        "total_hero_levels": total_hero_levels,
        "active_hero_level": active_hero_level,
    }