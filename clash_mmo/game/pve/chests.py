from __future__ import annotations

import random

from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.heroes import ENABLED_HERO_IDS


CHEST_CONFIG = {
    "common_chest": {
        "name": "Common War Chest",
        "gold": (150, 500),
        "clan_xp": (15, 60),
        "gems": (0, 1),
        "raid_medals": (0, 2),
        "gear_chance": 0.20,
        "gear_rarity_weights": {
            "common": 85,
            "rare": 15,
            "epic": 0,
            "legendary": 0,
        },
    },
    "rare_chest": {
        "name": "Rare War Chest",
        "gold": (500, 1200),
        "clan_xp": (50, 120),
        "gems": (0, 2),
        "raid_medals": (1, 4),
        "gear_chance": 0.45,
        "gear_rarity_weights": {
            "common": 45,
            "rare": 45,
            "epic": 10,
            "legendary": 0,
        },
    },
    "epic_chest": {
        "name": "Epic War Chest",
        "gold": (1000, 2200),
        "clan_xp": (100, 220),
        "gems": (1, 3),
        "raid_medals": (2, 6),
        "gear_chance": 0.75,
        "gear_rarity_weights": {
            "common": 15,
            "rare": 45,
            "epic": 35,
            "legendary": 5,
        },
    },
    "legend_chest": {
        "name": "Legend Chest",
        "gold": (1500, 3500),
        "clan_xp": (150, 350),
        "gems": (2, 5),
        "raid_medals": (4, 10),
        "gear_chance": 1.00,
        "gear_rarity_weights": {
            "common": 0,
            "rare": 35,
            "epic": 45,
            "legendary": 20,
        },
    },
}


PVE_CHEST_DROPS = {
    1: {
        "chest_key": "common_chest",
        "drop_chance": 0.35,
    },
    2: {
        "chest_key": "rare_chest",
        "drop_chance": 0.35,
    },
    3: {
        "chest_key": "epic_chest",
        "drop_chance": 0.35,
    },
}


def weighted_choice(weights: dict[str, int]) -> str:
    total = sum(max(0, int(weight or 0)) for weight in weights.values())

    if total <= 0:
        return next(iter(weights))

    roll = random.randint(1, total)
    running = 0

    for key, weight in weights.items():
        running += max(0, int(weight or 0))

        if roll <= running:
            return key

    return next(iter(weights))


def get_chest_name(chest_key: str) -> str:
    config = CHEST_CONFIG.get(str(chest_key or "").strip().lower())

    if not config:
        return str(chest_key)

    return str(config.get("name", chest_key))


def roll_pve_chest_drop(stars: int) -> str | None:
    stars = max(0, min(3, int(stars or 0)))

    if stars <= 0:
        return None

    drop_config = PVE_CHEST_DROPS.get(stars)

    if not drop_config:
        return None

    if random.random() > float(drop_config.get("drop_chance", 0) or 0):
        return None

    return str(drop_config.get("chest_key"))


def roll_chest_gear(chest_key: str, active_hero: str | None = None) -> str | None:
    chest_key = str(chest_key or "").strip().lower()
    config = CHEST_CONFIG.get(chest_key)

    if not config:
        return None

    if random.random() > float(config.get("gear_chance", 0) or 0):
        return None

    rarity = weighted_choice(config.get("gear_rarity_weights", {"common": 100}))

    active_hero = str(active_hero or "").strip().lower()
    use_active_pool = (
        bool(active_hero)
        and active_hero in ENABLED_HERO_IDS
        and random.random() < 0.70
    )

    candidates = [
        item_id
        for item_id, item in GEAR_CATALOG.items()
        if str(item.get("rarity", "common")).lower() == rarity
        and str(item.get("hero", "")).strip().lower() in ENABLED_HERO_IDS
        and (
            not use_active_pool
            or str(item.get("hero", "")).strip().lower() == active_hero
        )
    ]

    if not candidates and use_active_pool:
        candidates = [
            item_id
            for item_id, item in GEAR_CATALOG.items()
            if str(item.get("rarity", "common")).lower() == rarity
            and str(item.get("hero", "")).strip().lower() in ENABLED_HERO_IDS
        ]

    if not candidates:
        return None

    return random.choice(candidates)


def roll_chest_rewards(chest_key: str, active_hero: str | None = None) -> dict:
    chest_key = str(chest_key or "").strip().lower()
    config = CHEST_CONFIG.get(chest_key)

    if not config:
        raise ValueError(f"Unknown chest type: {chest_key}")

    gear_drop = roll_chest_gear(chest_key, active_hero)

    return {
        "chest_key": chest_key,
        "chest_name": str(config.get("name", chest_key)),
        "gold": random.randint(*config["gold"]),
        "clan_xp": random.randint(*config["clan_xp"]),
        "gems": random.randint(*config["gems"]),
        "raid_medals": random.randint(*config["raid_medals"]),
        "gear_drop": gear_drop,
    }