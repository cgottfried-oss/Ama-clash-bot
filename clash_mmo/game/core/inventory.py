from __future__ import annotations

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



def make_equipment_item(
    item_id: str,
    slot: str,
    rarity: str = "common",
    level: int = 1,
    stat_modifiers: dict | None = None,
):
    return {
        "item_id": item_id,
        "slot": slot,
        "rarity": normalize_rarity(rarity),
        "level": max(1, int(level)),
        "stat_modifiers": stat_modifiers or {},
    }