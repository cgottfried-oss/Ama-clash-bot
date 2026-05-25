from __future__ import annotations

import random

from .gear_catalog import GEAR_CATALOG


RARITY_WEIGHTS = {
    "common": 60,
    "rare": 28,
    "epic": 10,
    "legendary": 2,
}



def weighted_rarity_roll():
    table = []

    for rarity, weight in RARITY_WEIGHTS.items():
        table.extend([rarity] * weight)

    return random.choice(table)



def roll_equipment_drop():
    rarity = weighted_rarity_roll()

    valid_items = [
        (item_id, item)
        for item_id, item in GEAR_CATALOG.items()
        if item.get("rarity") == rarity
    ]

    if not valid_items:
        valid_items = list(GEAR_CATALOG.items())

    item_id, item = random.choice(valid_items)

    return {
        "item_id": item_id,
        "item": item,
    }
