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



def equip_item(profile: dict, item_id: str):
    inventory = profile.setdefault("inventory", {})
    items = inventory.setdefault("items", [])
    equipment = inventory.setdefault("equipment", {})

    for item in items:
        if item.get("item_id") != item_id:
            continue

        equipment[item["slot"]] = item
        return {
            "ok": True,
            "item": item,
        }

    return {
        "ok": False,
        "error": "Item not owned.",
    }



def get_equipped_items(profile: dict):
    inventory = profile.setdefault("inventory", {})
    equipment = inventory.setdefault("equipment", {})

    return [
        item
        for item in equipment.values()
        if item
    ]



def get_effective_profile_stats(profile: dict):
    base = profile.get("stats", {})

    base_block = StatBlock(
        attack=float(base.get("attack", 0)),
        defense=float(base.get("defense", 0)),
        health=float(base.get("health", 0)),
        speed=float(base.get("speed", 0)),
        crit=float(base.get("crit", 0)),
    )

    return calculate_effective_stats(
        base_block,
        get_equipped_items(profile),
    )



def unlock_hero(profile: dict, hero_id: str):
    heroes = profile.setdefault("heroes", {})

    heroes.setdefault(hero_id, {
        "level": 1,
        "abilities": [],
        "equipped_ability": None,
    })

    return heroes[hero_id]



def equip_hero_ability(profile: dict, hero_id: str, ability_id: str):
    heroes = profile.setdefault("heroes", {})

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