TERRITORY_REGIONS = {
    "north_forest": {
        "name": "North Forest",
        "emoji": "🌲",
        "base_income": {"gold": 250, "elixir": 120},
        "defense_bonus": 5,
    },
    "crystal_caverns": {
        "name": "Crystal Caverns",
        "emoji": "💎",
        "base_income": {"gold": 150, "gems": 1, "shiny_ore": 5},
        "defense_bonus": 8,
    },
    "dark_mire": {
        "name": "Dark Mire",
        "emoji": "🟣",
        "base_income": {"dark_elixir": 35, "gold": 120},
        "defense_bonus": 10,
    },
    "war_peak": {
        "name": "War Peak",
        "emoji": "⛰️",
        "base_income": {"raid_medals": 2, "clan_xp": 15},
        "defense_bonus": 14,
    },
}


def region_name(region_id: str) -> str:
    region = TERRITORY_REGIONS.get(region_id, {})
    return region.get("name", str(region_id).replace("_", " ").title())


def region_emoji(region_id: str) -> str:
    return TERRITORY_REGIONS.get(region_id, {}).get("emoji", "🏳️")
