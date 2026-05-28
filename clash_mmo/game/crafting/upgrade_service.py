from __future__ import annotations

from clash_mmo.game.core.inventory import ensure_item_instance_id
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG

from .upgrades import (
    MAX_GEAR_UPGRADE_LEVEL,
    get_display_name,
    get_next_upgrade_cost,
    get_stat_multiplier,
    get_upgrade_level,
)



def _players(state: dict) -> dict:
    return state.setdefault("players", {})



def _profile(state: dict, user_id: str) -> dict | None:
    return _players(state).get(str(user_id))



def _inventory(profile: dict) -> dict:
    return profile.setdefault("inventory", {})



def _currencies(profile: dict) -> dict:
    return _inventory(profile).setdefault("currencies", {})



def _items(profile: dict) -> list:
    return _inventory(profile).setdefault("items", [])



def _find_item(profile: dict, instance_id: str) -> dict | None:
    target = str(instance_id or "").strip()
    for item in _items(profile):
        if not isinstance(item, dict):
            continue
        current_id = ensure_item_instance_id(item)
        if current_id == target:
            return item
    return None



def upgrade_item(state: dict, user_id: str, item_instance_id: str) -> dict:
    profile = _profile(state, str(user_id))
    if not profile:
        return {"ok": False, "error": "Player profile not found."}

    item = _find_item(profile, item_instance_id)
    if not item:
        return {"ok": False, "error": "Item not found."}

    rarity = str(item.get("rarity") or "common").lower()
    current_upgrade = get_upgrade_level(item)

    if current_upgrade >= MAX_GEAR_UPGRADE_LEVEL:
        return {"ok": False, "error": f"This item is already +{MAX_GEAR_UPGRADE_LEVEL}."}

    cost = get_next_upgrade_cost(rarity, current_upgrade)

    currencies = _currencies(profile)

    for currency, amount in cost.items():
        if int(currencies.get(currency, 0) or 0) < int(amount or 0):
            readable = currency.replace("_", " ").title()
            return {
                "ok": False,
                "error": f"Not enough {readable}.",
            }

    for currency, amount in cost.items():
        currencies[currency] = int(currencies.get(currency, 0) or 0) - int(amount or 0)

    new_upgrade_level = current_upgrade + 1

    item["upgrade_level"] = new_upgrade_level
    item["plus"] = new_upgrade_level

    item["stat_multiplier"] = round(get_stat_multiplier(new_upgrade_level), 4)

    item_id = str(item.get("item_id") or "unknown")
    gear = GEAR_CATALOG.get(item_id, {})

    base_name = str(gear.get("name") or item_id.replace("_", " ").title())

    item["display_name"] = get_display_name(base_name, new_upgrade_level)

    crafting = state.setdefault("crafting", {})
    upgrade_log = crafting.setdefault("upgrade_log", [])

    upgrade_log.append({
        "user_id": str(user_id),
        "item_id": item_id,
        "instance_id": item_instance_id,
        "upgrade_level": new_upgrade_level,
        "cost": dict(cost),
    })

    while len(upgrade_log) > 200:
        upgrade_log.pop(0)

    return {
        "ok": True,
        "item": item,
        "cost": cost,
        "upgrade_level": new_upgrade_level,
    }
