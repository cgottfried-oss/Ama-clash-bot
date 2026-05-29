from __future__ import annotations


TOWN_HALL_UPGRADE_COSTS = {
    2: {"gold": 1_000, "elixir": 450, "clan_xp": 100},
    3: {"gold": 2_500, "elixir": 1_200, "clan_xp": 275},
    4: {"gold": 6_000, "elixir": 3_000, "clan_xp": 750},
    5: {"gold": 12_500, "elixir": 6_500, "clan_xp": 1_600},
    6: {"gold": 25_000, "elixir": 13_000, "clan_xp": 3_200},
    7: {"gold": 45_000, "elixir": 24_000, "clan_xp": 5_800},
    8: {"gold": 75_000, "elixir": 42_000, "clan_xp": 9_000},
    9: {"gold": 120_000, "elixir": 70_000, "clan_xp": 14_000},
    10: {"gold": 185_000, "elixir": 110_000, "clan_xp": 21_000},
    11: {"gold": 275_000, "elixir": 170_000, "clan_xp": 31_000},
    12: {"gold": 400_000, "elixir": 255_000, "clan_xp": 45_000},
    13: {"gold": 575_000, "elixir": 375_000, "clan_xp": 64_000},
    14: {"gold": 820_000, "elixir": 540_000, "clan_xp": 90_000},
    15: {"gold": 1_150_000, "elixir": 760_000, "clan_xp": 125_000},
    16: {"gold": 1_600_000, "elixir": 1_050_000, "clan_xp": 170_000},
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
        {"gold": 999_999_999, "elixir": 999_999_999, "clan_xp": 999_999_999},
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