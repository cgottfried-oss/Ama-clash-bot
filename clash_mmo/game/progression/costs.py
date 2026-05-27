from __future__ import annotations


TOWN_HALL_UPGRADE_COSTS = {
    2: {"gold": 750, "clan_xp": 50},
    3: {"gold": 1_500, "clan_xp": 125},
    4: {"gold": 3_000, "clan_xp": 250},
    5: {"gold": 5_500, "clan_xp": 450},
    6: {"gold": 8_500, "clan_xp": 700},
    7: {"gold": 13_000, "clan_xp": 1_050},
    8: {"gold": 19_000, "clan_xp": 1_500},
    9: {"gold": 27_000, "clan_xp": 2_100},
    10: {"gold": 38_000, "clan_xp": 2_900},
    11: {"gold": 52_000, "clan_xp": 3_900},
    12: {"gold": 70_000, "clan_xp": 5_200},
    13: {"gold": 92_000, "clan_xp": 6_800},
    14: {"gold": 120_000, "clan_xp": 8_800},
    15: {"gold": 155_000, "clan_xp": 11_200},
    16: {"gold": 200_000, "clan_xp": 14_000},
}


HERO_BASE_UPGRADE_COSTS = {
    "king": {"gold": 1_200, "clan_xp": 75},
    "queen": {"gold": 1_500, "clan_xp": 90},
    "warden": {"gold": 1_800, "clan_xp": 110},

    # Royal Champion disabled until gear exists.
    # "royal_champion": {"gold": 2_100, "clan_xp": 130},
}


def get_town_hall_upgrade_cost(current_town_hall: int) -> dict:
    next_town_hall = int(current_town_hall or 1) + 1

    return TOWN_HALL_UPGRADE_COSTS.get(
        next_town_hall,
        {"gold": 999_999_999, "clan_xp": 999_999_999},
    )


def get_hero_upgrade_cost(hero_id: str, current_level: int) -> dict:
    hero_id = str(hero_id or "").strip().lower()
    current_level = max(1, int(current_level or 1))

    base = HERO_BASE_UPGRADE_COSTS.get(
        hero_id,
        {"gold": 1_500, "clan_xp": 100},
    )

    multiplier = current_level + 1

    return {
        "gold": int(base["gold"] * multiplier * 1.15),
        "clan_xp": int(base["clan_xp"] * multiplier * 1.10),
    }