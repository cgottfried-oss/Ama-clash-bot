EQUIPMENT_SLOTS = [
    "weapon",
    "armor",
    "trinket",
]

GEAR_CATALOG = {
    "rusty_sword": {
        "name": "Rusty Sword",
        "slot": "weapon",
        "rarity": "common",
        "hero": "any",
        "power": 5,
    },
    "warrior_plate": {
        "name": "Warrior Plate",
        "slot": "armor",
        "rarity": "rare",
        "hero": "barbarian_king",
        "power": 12,
    },
    "eagle_bow": {
        "name": "Eagle Bow",
        "slot": "weapon",
        "rarity": "epic",
        "hero": "archer_queen",
        "power": 20,
        "ability": "royal_cloak",
    },
    "warden_tome": {
        "name": "Warden Tome",
        "slot": "trinket",
        "rarity": "legendary",
        "hero": "grand_warden",
        "power": 28,
        "ability": "eternal_tome",
    },
}


def get_gear(item_id: str) -> dict | None:
    return GEAR_CATALOG.get(item_id)
