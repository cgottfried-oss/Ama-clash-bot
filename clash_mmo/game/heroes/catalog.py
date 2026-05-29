from __future__ import annotations

HERO_ORDER = [
    "barbarian_king",
    "archer_queen",
    "grand_warden",
    "royal_champion",
]

HERO_UNLOCKS = {
    "barbarian_king": 7,
    "archer_queen": 9,
    "grand_warden": 11,
    "royal_champion": 13,
}

HERO_CATALOG = {
    "barbarian_king": {
        "name": "Barbarian King",
        "emoji": "👑",
        "role": "Tank / Bruiser",
        "description": "Front-line hero with strong Gold raid and PvE power.",
        "unlock_town_hall": 7,
        "base_power": 25,
        "power_per_level": 4,
        "primary_resource": "dark_elixir",
        "abilities": {
            "iron_fist": {"name": "Iron Fist", "unlock_level": 1, "power_bonus": 10},
            "rage_aura": {"name": "Rage Aura", "unlock_level": 5, "power_bonus": 18},
            "earthbreaker": {"name": "Earthbreaker", "unlock_level": 10, "power_bonus": 30},
        },
    },
    "archer_queen": {
        "name": "Archer Queen",
        "emoji": "🏹",
        "role": "Ranged DPS",
        "description": "High-damage hero with stronger PvE and raid consistency.",
        "unlock_town_hall": 9,
        "base_power": 28,
        "power_per_level": 5,
        "primary_resource": "dark_elixir",
        "abilities": {
            "royal_cloak": {"name": "Royal Cloak", "unlock_level": 1, "power_bonus": 12},
            "piercing_shot": {"name": "Piercing Shot", "unlock_level": 5, "power_bonus": 20},
            "eagle_eye": {"name": "Eagle Eye", "unlock_level": 10, "power_bonus": 34},
        },
    },
    "grand_warden": {
        "name": "Grand Warden",
        "emoji": "📘",
        "role": "Support / Aura",
        "description": "Support hero with bonus progression value and raid utility.",
        "unlock_town_hall": 11,
        "base_power": 30,
        "power_per_level": 5,
        "primary_resource": "elixir",
        "abilities": {
            "eternal_tome": {"name": "Eternal Tome", "unlock_level": 1, "power_bonus": 14},
            "life_aura": {"name": "Life Aura", "unlock_level": 5, "power_bonus": 22},
            "healing_tome": {"name": "Healing Tome", "unlock_level": 10, "power_bonus": 36},
        },
    },
    "royal_champion": {
        "name": "Royal Champion",
        "emoji": "🛡️",
        "role": "Burst / Cleanup",
        "description": "Late-game hero with high PvP and boss damage scaling.",
        "unlock_town_hall": 13,
        "base_power": 34,
        "power_per_level": 6,
        "primary_resource": "dark_elixir",
        "abilities": {
            "seeking_shield": {"name": "Seeking Shield", "unlock_level": 1, "power_bonus": 16},
            "rocket_spear": {"name": "Rocket Spear", "unlock_level": 5, "power_bonus": 26},
            "electro_boots": {"name": "Electro Boots", "unlock_level": 10, "power_bonus": 40},
        },
    },
}


def enabled_hero_ids() -> list[str]:
    return list(HERO_ORDER)


def hero_display_name(hero_id: str) -> str:
    return HERO_CATALOG.get(hero_id, {}).get("name", str(hero_id).replace("_", " ").title())


def unlocked_hero_ids_for_town_hall(town_hall: int) -> list[str]:
    town_hall = int(town_hall or 1)
    return [hero_id for hero_id in HERO_ORDER if town_hall >= int(HERO_CATALOG[hero_id].get("unlock_town_hall", 1))]
