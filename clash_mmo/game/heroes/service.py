from __future__ import annotations

from clash_mmo.game.heroes.catalog import HERO_CATALOG
from clash_mmo.game.heroes.loadouts import ensure_hero_loadout, normalize_hero_loadouts
from clash_mmo.game.heroes.progression import MAX_HERO_LEVEL, get_hero_upgrade_cost, get_hero_xp_needed


def unlock_hero(profile: dict, hero_id: str) -> bool:
    if hero_id not in HERO_CATALOG:
        return False
    heroes = normalize_hero_loadouts(profile)
    if hero_id in heroes:
        ensure_hero_loadout(profile, hero_id)
        return False
    ensure_hero_loadout(profile, hero_id)
    if not profile.get("active_hero"):
        profile["active_hero"] = hero_id
    return True


def can_upgrade_hero(profile: dict, hero_id: str) -> tuple[bool, str]:
    heroes = normalize_hero_loadouts(profile)
    hero = heroes.get(hero_id)
    if not hero:
        return False, "Hero is not unlocked."
    level = int(hero.get("level", 1) or 1)
    if level >= MAX_HERO_LEVEL:
        return False, "Hero is already max level."
    needed_xp = get_hero_xp_needed(level)
    if int(hero.get("xp", 0) or 0) < needed_xp:
        return False, f"Hero needs {needed_xp:,} XP to upgrade."
    cost = get_hero_upgrade_cost(hero_id, level)
    for resource, amount in cost.items():
        if int(profile.get(resource, 0) or 0) < int(amount):
            return False, f"Not enough {resource.replace('_', ' ').title()}. Need {int(amount):,}."
    return True, "OK"


def upgrade_hero(profile: dict, hero_id: str) -> tuple[bool, str]:
    ok, message = can_upgrade_hero(profile, hero_id)
    if not ok:
        return False, message
    hero = ensure_hero_loadout(profile, hero_id)
    level = int(hero.get("level", 1) or 1)
    needed_xp = get_hero_xp_needed(level)
    cost = get_hero_upgrade_cost(hero_id, level)
    for resource, amount in cost.items():
        profile[resource] = max(0, int(profile.get(resource, 0) or 0) - int(amount))
    hero["xp"] = max(0, int(hero.get("xp", 0) or 0) - needed_xp)
    hero["level"] = level + 1
    return True, f"Upgraded {HERO_CATALOG[hero_id]['name']} to level {hero['level']}."


def add_hero_xp(profile: dict, amount: int, hero_id: str | None = None) -> tuple[bool, str]:
    heroes = normalize_hero_loadouts(profile)
    if not heroes:
        return False, "No heroes unlocked."
    hero_id = hero_id or profile.get("active_hero") or next(iter(heroes.keys()))
    if hero_id not in heroes:
        return False, "Hero is not unlocked."
    hero = ensure_hero_loadout(profile, hero_id)
    hero["xp"] = max(0, int(hero.get("xp", 0) or 0) + max(0, int(amount or 0)))
    return True, f"Added {int(amount):,} XP to {HERO_CATALOG.get(hero_id, {}).get('name', hero_id)}."
