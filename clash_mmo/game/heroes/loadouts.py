from __future__ import annotations

from clash_mmo.game.heroes.catalog import HERO_CATALOG, HERO_ORDER


DEFAULT_HERO_STATE = {
    "level": 1,
    "xp": 0,
    "equipment": {},
    "equipped_ability": None,
}


def normalize_hero_loadouts(profile: dict) -> dict:
    heroes = profile.setdefault("heroes", {})
    if not isinstance(heroes, dict):
        heroes = {}
        profile["heroes"] = heroes

    for hero_id in HERO_ORDER:
        if hero_id not in heroes:
            continue
        if not isinstance(heroes[hero_id], dict):
            heroes[hero_id] = dict(DEFAULT_HERO_STATE)
        heroes[hero_id].setdefault("level", 1)
        heroes[hero_id].setdefault("xp", 0)
        heroes[hero_id].setdefault("equipment", {})
        heroes[hero_id].setdefault("equipped_ability", None)

    return heroes


def ensure_hero_loadout(profile: dict, hero_id: str) -> dict:
    heroes = normalize_hero_loadouts(profile)
    hero_id = str(hero_id)
    heroes.setdefault(hero_id, dict(DEFAULT_HERO_STATE))
    heroes[hero_id].setdefault("level", 1)
    heroes[hero_id].setdefault("xp", 0)
    heroes[hero_id].setdefault("equipment", {})
    heroes[hero_id].setdefault("equipped_ability", None)
    return heroes[hero_id]


def set_active_hero(profile: dict, hero_id: str) -> bool:
    heroes = normalize_hero_loadouts(profile)
    if hero_id not in heroes:
        return False
    profile["active_hero"] = hero_id
    return True


def get_active_hero(profile: dict) -> tuple[str | None, dict | None]:
    heroes = normalize_hero_loadouts(profile)
    active = profile.get("active_hero")
    if active in heroes:
        return active, heroes[active]
    if heroes:
        first = next(iter(heroes.keys()))
        profile["active_hero"] = first
        return first, heroes[first]
    return None, None
