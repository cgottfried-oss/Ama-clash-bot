from __future__ import annotations

from clash_mmo.game.heroes.catalog import HERO_CATALOG
from clash_mmo.game.heroes.loadouts import normalize_hero_loadouts


MAX_HERO_LEVEL = 30


def get_hero_xp_needed(level: int) -> int:
    level = max(1, int(level or 1))
    return 100 + ((level - 1) * 50)


def get_hero_upgrade_cost(hero_id: str, level: int) -> dict:
    hero = HERO_CATALOG.get(hero_id, {})
    resource = hero.get("primary_resource", "dark_elixir")
    level = max(1, int(level or 1))
    base = 250 if resource == "elixir" else 80
    return {resource: base + ((level - 1) * base // 2)}


def _ability_power(hero_id: str, level: int, equipped_ability: str | None) -> int:
    if not equipped_ability:
        return 0
    abilities = HERO_CATALOG.get(hero_id, {}).get("abilities", {})
    ability = abilities.get(equipped_ability)
    if not ability:
        return 0
    if int(level or 1) < int(ability.get("unlock_level", 1)):
        return 0
    return int(ability.get("power_bonus", 0) or 0)


def get_total_hero_power(profile: dict) -> int:
    heroes = normalize_hero_loadouts(profile)
    total = 0
    for hero_id, hero_state in heroes.items():
        hero = HERO_CATALOG.get(hero_id)
        if not hero:
            continue
        level = max(1, int(hero_state.get("level", 1) or 1))
        total += int(hero.get("base_power", 0) or 0)
        total += (level - 1) * int(hero.get("power_per_level", 0) or 0)
        total += _ability_power(hero_id, level, hero_state.get("equipped_ability"))
    return total
