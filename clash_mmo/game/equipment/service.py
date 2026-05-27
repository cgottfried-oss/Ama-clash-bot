from __future__ import annotations

from ..core.inventory import make_equipment_item
from ..core.modifiers import StatBlock, calculate_effective_stats
from .abilities import HERO_ABILITIES
from .gear_catalog import GEAR_CATALOG



def grant_equipment(profile: dict, item_id: str):
    gear = GEAR_CATALOG.get(item_id)

    if not gear:
        return False

    inventory = profile.setdefault("inventory", {})
    inventory.setdefault("items", [])

    inventory["items"].append(
        make_equipment_item(
            item_id=item_id,
            slot=gear["slot"],
            rarity=gear["rarity"],
            stat_modifiers=gear.get("stats", {}),
        )
    )

    return True

def normalize_hero_loadouts(profile: dict):
    heroes = profile.setdefault("heroes", {})

    for hero_id, hero_data in list(heroes.items()):
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

def equip_item(profile: dict, hero_id: str, item_id: str):
    hero_id = str(hero_id or "").strip().lower()
    item_id = str(item_id or "").strip().lower()

    heroes = normalize_hero_loadouts(profile)

    if hero_id not in heroes:
        return {
            "ok": False,
            "error": "Hero not unlocked.",
        }

    gear = GEAR_CATALOG.get(item_id)

    if not gear:
        return {
            "ok": False,
            "error": "Gear not found.",
        }

    required_hero = str(gear.get("hero", "")).strip().lower()

    if required_hero and required_hero != hero_id:
        required_hero_name = required_hero.replace("_", " ").title()
        return {
            "ok": False,
            "error": f"This gear can only be equipped by {required_hero_name}.",
        }

    inventory = profile.setdefault("inventory", {})
    items = inventory.setdefault("items", [])

    hero_equipment = heroes[hero_id].setdefault("equipment", {})

    for item in items:
        if str(item.get("item_id", "")).strip().lower() != item_id:
            continue

        slot = item.get("slot") or gear.get("slot")

        if not slot:
            return {
                "ok": False,
                "error": "Gear slot missing.",
            }

        hero_equipment[slot] = item

        return {
            "ok": True,
            "item": item,
            "hero_id": hero_id,
        }

    return {
        "ok": False,
        "error": "Item not owned.",
    }



def get_equipped_items(profile: dict, hero_id: str | None = None):
    heroes = normalize_hero_loadouts(profile)

    if hero_id:
        hero = heroes.get(hero_id)

        if not hero:
            return []

        equipment = hero.setdefault("equipment", {})

        return [
            item
            for item in equipment.values()
            if item
        ]

    equipped = []

    for hero in heroes.values():
        equipment = hero.setdefault("equipment", {})

        equipped.extend([
            item
            for item in equipment.values()
            if item
        ])

    return equipped



def get_effective_profile_stats(profile: dict):
    base = profile.get("stats", {})

    base_block = StatBlock(
        attack=float(base.get("attack", 0)),
        defense=float(base.get("defense", 0)),
        health=float(base.get("health", 0)),
        speed=float(base.get("speed", 0)),
        crit=float(base.get("crit", 0)),
    )

    active_hero = profile.get("active_hero")

    return calculate_effective_stats(
        base_block,
        get_equipped_items(profile, active_hero),
    )



def unlock_hero(profile: dict, hero_id: str):
    heroes = normalize_hero_loadouts(profile)

    heroes.setdefault(hero_id, {
        "level": 1,
        "abilities": [],
        "equipped_ability": None,
        "equipment": {},
    })
    if not profile.get("active_hero"):
        profile["active_hero"] = hero_id

    return heroes[hero_id]



def equip_hero_ability(profile: dict, hero_id: str, ability_id: str):
    heroes = normalize_hero_loadouts(profile)

    if hero_id not in heroes:
        return {
            "ok": False,
            "error": "Hero not unlocked.",
        }

    ability = HERO_ABILITIES.get(ability_id)

    if not ability:
        return {
            "ok": False,
            "error": "Ability not found.",
        }

    if ability.get("hero") != hero_id:
        return {
            "ok": False,
            "error": "Ability incompatible with hero.",
        }

    heroes[hero_id]["equipped_ability"] = ability_id

    if ability_id not in heroes[hero_id]["abilities"]:
        heroes[hero_id]["abilities"].append(ability_id)

    return {
        "ok": True,
        "ability": ability,
    }