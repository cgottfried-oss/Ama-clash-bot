HERO_CATALOG = {
    "barbarian_king": {
        "name": "Barbarian King",
        "role": "Tank / bruiser",
        "unlocks_at_th": 7,
        "base_power": 25,
        "power_per_level": 4,
        "abilities": ["Iron Fist", "Rage Aura", "Earthbreaker"],
    },
    "archer_queen": {
        "name": "Archer Queen",
        "role": "Ranged DPS",
        "unlocks_at_th": 9,
        "base_power": 28,
        "power_per_level": 5,
        "abilities": ["Royal Cloak", "Piercing Shot", "Eagle Eye"],
    },
    "grand_warden": {
        "name": "Grand Warden",
        "role": "Support / aura",
        "unlocks_at_th": 11,
        "base_power": 30,
        "power_per_level": 5,
        "abilities": ["Eternal Tome", "Life Aura", "Healing Tome"],
    },
    "royal_champion": {
        "name": "Royal Champion",
        "role": "Burst / cleanup",
        "unlocks_at_th": 13,
        "base_power": 34,
        "power_per_level": 6,
        "abilities": ["Seeking Shield", "Rocket Spear", "Electro Boots"],
    },
}


def unlocked_heroes_for_th(town_hall: int) -> list[str]:
    return [hero_id for hero_id, data in HERO_CATALOG.items() if int(town_hall or 1) >= int(data.get("unlocks_at_th", 1))]


def hero_display_name(hero_id: str) -> str:
    return HERO_CATALOG.get(hero_id, {}).get("name", hero_id.replace("_", " ").title())
