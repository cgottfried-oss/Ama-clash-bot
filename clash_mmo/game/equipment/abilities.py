HERO_ABILITIES = {
    "iron_fist": {
        "name": "Iron Fist",
        "hero": "barbarian_king",
        "effect": "Boost raid damage and PvE attacks.",
        "power_bonus": 10,
    },
    "royal_cloak": {
        "name": "Royal Cloak",
        "hero": "archer_queen",
        "effect": "Increase raid success and precision damage.",
        "power_bonus": 12,
    },
    "eternal_tome": {
        "name": "Eternal Tome",
        "hero": "grand_warden",
        "effect": "Protect party and increase support value.",
        "power_bonus": 14,
    },
    "seeking_shield": {
        "name": "Seeking Shield",
        "hero": "royal_champion",
        "effect": "Burst damage bonus against bosses and players.",
        "power_bonus": 16,
    },
}


def ability_display_name(ability_id: str) -> str:
    return HERO_ABILITIES.get(ability_id, {}).get("name", str(ability_id).replace("_", " ").title())
