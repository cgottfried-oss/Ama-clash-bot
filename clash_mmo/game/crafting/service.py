from __future__ import annotations

from clash_mmo.game.core.inventory import ensure_item_instance_id

from .salvage import get_salvage_rewards



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



def _is_equipped(profile: dict, item_instance_id: str) -> bool:
    target = str(item_instance_id or "").strip()

    heroes = profile.get("heroes", {})
    if isinstance(heroes, dict):
        for hero_data in heroes.values():
            if not isinstance(hero_data, dict):
                continue
            equipment = hero_data.get("equipment", {})
            if not isinstance(equipment, dict):
                continue
            for equipped in equipment.values():
                if isinstance(equipped, dict) and str(equipped.get("instance_id") or "") == target:
                    return True

    inventory_equipment = _inventory(profile).get("equipment", {})
    if isinstance(inventory_equipment, dict):
        for equipped in inventory_equipment.values():
            if isinstance(equipped, dict) and str(equipped.get("instance_id") or "") == target:
                return True

    return False



def salvage_item(state: dict, user_id: str, item_instance_id: str) -> dict:
    user_id = str(user_id)
    item_instance_id = str(item_instance_id or "").strip()

    profile = _profile(state, user_id)
    if not profile:
        return {"ok": False, "error": "Player profile not found."}

    if _is_equipped(profile, item_instance_id):
        return {"ok": False, "error": "Unequip this item before salvaging it."}

    items = _items(profile)

    found_index = None
    found_item = None

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        instance_id = ensure_item_instance_id(item)

        if instance_id == item_instance_id:
            found_index = index
            found_item = item
            break

    if found_index is None or found_item is None:
        return {"ok": False, "error": "Item not found in inventory."}

    rarity = str(found_item.get("rarity") or "common").lower()

    rewards = get_salvage_rewards(rarity)

    removed_item = items.pop(found_index)

    currencies = _currencies(profile)

    for currency, amount in rewards.items():
        currencies[currency] = int(currencies.get(currency, 0) or 0) + int(amount or 0)

    crafting = state.setdefault("crafting", {})
    salvage_log = crafting.setdefault("salvage_log", [])

    salvage_log.append({
        "user_id": user_id,
        "item_id": removed_item.get("item_id"),
        "instance_id": item_instance_id,
        "rarity": rarity,
        "rewards": dict(rewards),
    })

    while len(salvage_log) > 100:
        salvage_log.pop(0)

    return {
        "ok": True,
        "item": removed_item,
        "rewards": rewards,
    }
