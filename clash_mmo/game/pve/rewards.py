from __future__ import annotations

import random

from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG


BOSS_RARITY_MULTIPLIERS = {
    "common": 1.0,
    "rare": 1.15,
    "epic": 1.35,
    "legendary": 1.65,
}


LEGEND_CHEST_DROP_CHANCE = {
    "common": 1.00,
    "rare": 1.00,
    "epic": 1.00,
    "legendary": 1.00,
}


BOSS_GEAR_DROP_CHANCE = {
    "common": 1.00,
    "rare": 1.00,
    "epic": 1.00,
    "legendary": 1.00,
}


GEAR_RARITY_WEIGHTS_BY_BOSS = {
    "common": {
        "common": 90,
        "rare": 10,
        "epic": 0,
        "legendary": 0,
    },
    "rare": {
        "common": 65,
        "rare": 30,
        "epic": 5,
        "legendary": 0,
    },
    "epic": {
        "common": 45,
        "rare": 35,
        "epic": 18,
        "legendary": 2,
    },
    "legendary": {
        "common": 25,
        "rare": 35,
        "epic": 30,
        "legendary": 10,
    },
}


def _weighted_choice(weight_map: dict[str, int]) -> str:
    total = sum(max(0, int(weight or 0)) for weight in weight_map.values())

    if total <= 0:
        return next(iter(weight_map.keys()))

    roll = random.uniform(0, total)
    current = 0

    for key, weight in weight_map.items():
        current += max(0, int(weight or 0))

        if roll <= current:
            return key

    return next(iter(weight_map.keys()))


def _roll_gear_drop(boss_rarity: str, active_hero: str | None = None) -> str | None:
    boss_rarity = str(boss_rarity or "epic").lower()

    drop_chance = BOSS_GEAR_DROP_CHANCE.get(boss_rarity, 0.10)

    if random.random() > drop_chance:
        return None

    rarity_weights = GEAR_RARITY_WEIGHTS_BY_BOSS.get(
        boss_rarity,
        GEAR_RARITY_WEIGHTS_BY_BOSS["epic"],
    )

    gear_rarity = _weighted_choice(rarity_weights)

    active_hero = str(active_hero or "").strip().lower()

    use_active_hero_pool = bool(active_hero) and random.random() < 0.70

    candidates = [
        item_id
        for item_id, item in GEAR_CATALOG.items()
        if str(item.get("rarity", "common")).lower() == gear_rarity
        and (
            not use_active_hero_pool
            or str(item.get("hero", "")).strip().lower() == active_hero
        )
    ]

    if not candidates and use_active_hero_pool:
        candidates = [
            item_id
            for item_id, item in GEAR_CATALOG.items()
            if str(item.get("rarity", "common")).lower() == gear_rarity
        ]

    if not candidates:
        candidates = list(GEAR_CATALOG.keys())

    if not candidates:
        return None

    return random.choice(candidates)


def calculate_boss_defeat_rewards(
    *,
    player_damage: int,
    total_damage: int,
    boss_rarity: str = "epic",
    active_hero: str | None = None,
):
    player_damage = max(0, int(player_damage or 0))
    total_damage = max(1, int(total_damage or 1))
    boss_rarity = str(boss_rarity or "epic").lower()

    share = player_damage / total_damage
    rarity_multiplier = BOSS_RARITY_MULTIPLIERS.get(boss_rarity, 1.25)

    gold = int((250 + player_damage * 0.45 + share * 1200) * rarity_multiplier)
    gems = 1 if share >= 0.35 else 0

    if boss_rarity == "legendary":
        gems += 1

    medals = max(1, int(1 + share * 3))
    clan_xp = int((25 + share * 100) * rarity_multiplier)

    legend_chest_chance = LEGEND_CHEST_DROP_CHANCE.get(boss_rarity, 0.05)
    legend_chest = random.random() < legend_chest_chance

    gear_drop = _roll_gear_drop(boss_rarity, active_hero)

    return {
        "gold": gold,
        "gems": gems,
        "medals": medals,
        "clan_xp": clan_xp,
        "legend_chest": legend_chest,
        "legend_chest_chance": legend_chest_chance,
        "gear_drop": gear_drop,
        "share": share,
    }