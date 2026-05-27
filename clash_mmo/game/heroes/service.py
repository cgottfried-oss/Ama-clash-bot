from __future__ import annotations

from clash_mmo.game.equipment.service import normalize_hero_loadouts, unlock_hero
from clash_mmo.game.heroes.catalog import (
    HERO_CATALOG,
    enabled_hero_ids,
    get_hero_name,
    get_hero_unlock_th,
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


def get_profile_hero_level(profile: dict, hero_id: str) -> int:
    hero_id = str(hero_id or "").strip().lower()
    heroes = normalize_hero_loadouts(profile)
    hero_data = heroes.get(hero_id)

    if not isinstance(hero_data, dict):
        return 0

    return int(hero_data.get("level", 1) or 1)


def get_total_hero_power(profile: dict) -> int:
    total = 0

    for hero_id in enabled_hero_ids():
        total += get_profile_hero_level(profile, hero_id)

    return total


def hero_is_unlocked(profile: dict, hero_id: str) -> bool:
    hero_id = str(hero_id or "").strip().lower()
    heroes = normalize_hero_loadouts(profile)
    return isinstance(heroes.get(hero_id), dict)


def get_active_hero_id(profile: dict) -> str | None:
    active_hero = str(profile.get("active_hero") or "").strip().lower()

    if active_hero in HERO_CATALOG:
        return active_hero

    return None


def set_active_hero(profile: dict, hero_id: str) -> dict:
    hero_id = str(hero_id or "").strip().lower()

    if hero_id not in HERO_CATALOG:
        return {
            "ok": False,
            "error": "Invalid hero.",
        }

    heroes = normalize_hero_loadouts(profile)

    if not isinstance(heroes.get(hero_id), dict):
        return {
            "ok": False,
            "error": f"{get_hero_name(hero_id)} is not unlocked.",
        }

    profile["active_hero"] = hero_id

    return {
        "ok": True,
        "hero_id": hero_id,
        "hero_name": get_hero_name(hero_id),
    }