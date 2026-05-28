from __future__ import annotations

import uuid

from .rarity import normalize_rarity


EQUIPMENT_SLOTS = [
    "weapon",
    "helmet",
    "chest",
    "boots",
    "accessory",
]



def default_inventory():
    return {
        "currencies": {
            "gold": 0,
            "gems": 0,
            "raid_medals": 0,
            "dark_elixir": 0,
        },
        "items": [],
        "equipment": {
            slot: None
            for slot in EQUIPMENT_SLOTS
        },
    }



def make_item_stack(item_id: str, quantity: int = 1):
    return {
        "item_id": item_id,
        "quantity": max(1, int(quantity)),
    }



def ensure_item_instance_id(item: dict) -> str:
    instance_id = str(item.get("instance_id") or item.get("uid") or "").strip()
    if not instance_id:
        instance_id = str(uuid.uuid4())
        item["instance_id"] = instance_id
    return instance_id



def make_equipment_item(
    item_id: str,
    slot: str,
    rarity: str = "common",
    level: int = 1,
    stat_modifiers: dict | None = None,
):
    return {
        "instance_id": str(uuid.uuid4()),
        "item_id": item_id,
        "slot": slot,
        "rarity": normalize_rarity(rarity),
        "level": max(1, int(level)),
        "stat_modifiers": stat_modifiers or {},
    }
