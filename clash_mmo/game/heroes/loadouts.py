from __future__ import annotations

from clash_mmo.game.heroes.catalog import HERO_CATALOG, get_hero_name


def make_default_hero_loadout(hero_id: str) -> dict:
    hero_id = str(hero_id or "").strip().lower()

    return {
        "level": 1,
        "abilities": [],
        "equipped_ability": None,
        "equipment": {},
    }


def normalize_hero_loadouts(profile: dict) -> dict:
    heroes = profile.setdefault("heroes", {})

    for hero_id, hero_data in list(heroes.items()):
        hero_id = str(hero_id or "").strip().lower()

        if not isinstance(hero_data, dict):
            heroes[hero_id] = {
                "level": int(hero_data or 1),
                "abilities": [],
                "equipped_ability": None,
                "equipment": {},
            }
            continue

        hero_data.setdefault("level", 1)
        hero_data.setdefault("abilities", [])
        hero_data.setdefault("equipped_ability", None)
        hero_data.setdefault("equipment", {})

    if heroes and not profile.get("active_hero"):
        profile["active_hero"] = next(iter(heroes.keys()))

    return heroes


def unlock_hero(profile: dict, hero_id: str) -> dict:
    hero_id = str(hero_id or "").strip().lower()

    if hero_id not in HERO_CATALOG:
        raise ValueError(f"Unknown hero: {hero_id}")

    heroes = normalize_hero_loadouts(profile)

    heroes.setdefault(hero_id, make_default_hero_loadout(hero_id))

    if not profile.get("active_hero"):
        profile["active_hero"] = hero_id

    return heroes[hero_id]


def hero_is_unlocked(profile: dict, hero_id: str) -> bool:
    hero_id = str(hero_id or "").strip().lower()
    heroes = normalize_hero_loadouts(profile)

    return isinstance(heroes.get(hero_id), dict)


def get_profile_hero_level(profile: dict, hero_id: str) -> int:
    hero_id = str(hero_id or "").strip().lower()
    heroes = normalize_hero_loadouts(profile)
    hero_data = heroes.get(hero_id)

    if not isinstance(hero_data, dict):
        return 0

    return int(hero_data.get("level", 1) or 1)


def get_active_hero_id(profile: dict) -> str | None:
    active_hero = str(profile.get("active_hero") or "").strip().lower()

    if active_hero in HERO_CATALOG and hero_is_unlocked(profile, active_hero):
        return active_hero

    return None


def set_active_hero(profile: dict, hero_id: str) -> dict:
    hero_id = str(hero_id or "").strip().lower()

    if hero_id not in HERO_CATALOG:
        return {
            "ok": False,
            "error": "Invalid hero.",
        }

    if not hero_is_unlocked(profile, hero_id):
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