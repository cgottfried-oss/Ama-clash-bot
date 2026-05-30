from __future__ import annotations


ENABLED_HERO_IDS = {
    "king",
    "queen",
    "warden",
}


HERO_CATALOG = {
    "king": {
        "id": "king",
        "name": "King",
        "full_name": "Barbarian King",
        "unlock_th": 3,
        "role": "Tank / Bruiser",
        "base_upgrade_gold": 1_200,
        "base_upgrade_clan_xp": 75,
    },
    "queen": {
        "id": "queen",
        "name": "Queen",
        "full_name": "Archer Queen",
        "unlock_th": 5,
        "role": "Damage / Crit",
        "base_upgrade_gold": 1_500,
        "base_upgrade_clan_xp": 90,
    },
    "warden": {
        "id": "warden",
        "name": "Warden",
        "full_name": "Grand Warden",
        "unlock_th": 7,
        "role": "Support / Defense",
        "base_upgrade_gold": 1_800,
        "base_upgrade_clan_xp": 110,
    },

    # Royal Champion is intentionally disabled for now.
    # Re-enable after creating Royal Champion gear.
    # "royal_champion": {
    #     "id": "royal_champion",
    #     "name": "Royal Champion",
    #     "full_name": "Royal Champion",
    #     "unlock_th": 10,
    #     "role": "Burst / Strike",
    #     "base_upgrade_gold": 2_100,
    #     "base_upgrade_clan_xp": 130,
    # },
}


def is_enabled_hero(hero_id: str) -> bool:
    return str(hero_id or "").strip().lower() in ENABLED_HERO_IDS


def enabled_hero_ids() -> list[str]:
    return list(HERO_CATALOG.keys())


def get_hero_config(hero_id: str) -> dict | None:
    hero_id = str(hero_id or "").strip().lower()
    return HERO_CATALOG.get(hero_id)


def get_hero_name(hero_id: str, *, full: bool = False) -> str:
    hero_id = str(hero_id or "").strip().lower()
    config = HERO_CATALOG.get(hero_id)

    if not config:
        return hero_id.replace("_", " ").title()

    return str(config.get("full_name" if full else "name", hero_id))


def get_hero_unlock_th(hero_id: str) -> int:
    config = get_hero_config(hero_id)

    if not config:
        return 999

    return int(config.get("unlock_th", 999) or 999)


def unlocked_hero_ids_for_town_hall(town_hall: int) -> list[str]:
    town_hall = int(town_hall or 1)

    return [
        hero_id
        for hero_id, config in HERO_CATALOG.items()
        if town_hall >= int(config.get("unlock_th", 999) or 999)
    ]