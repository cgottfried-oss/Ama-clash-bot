from __future__ import annotations

from clash_mmo.game.heroes.catalog import (
    enabled_hero_ids,
    get_hero_unlock_th,
)
from clash_mmo.game.heroes.loadouts import (
    get_profile_hero_level,
    normalize_hero_loadouts,
    unlock_hero,
)


def ensure_unlocked_heroes_for_town_hall(profile: dict, town_hall: int) -> list[str]:
    unlocked = []

    town_hall = int(town_hall or 1)

    for hero_id in enabled_hero_ids():
        unlock_th = get_hero_unlock_th(hero_id)

        if town_hall >= unlock_th:
            unlock_hero(profile, hero_id)
            unlocked.append(hero_id)

    heroes = normalize_hero_loadouts(profile)

    if unlocked and not profile.get("active_hero"):
        profile["active_hero"] = unlocked[0]

    if profile.get("active_hero") not in heroes and unlocked:
        profile["active_hero"] = unlocked[0]

    return unlocked


def get_total_hero_power(profile: dict) -> int:
    total = 0

    for hero_id in enabled_hero_ids():
        total += get_profile_hero_level(profile, hero_id)

    return total