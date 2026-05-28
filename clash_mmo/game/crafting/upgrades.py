from __future__ import annotations

MAX_GEAR_UPGRADE_LEVEL = 12

RARITY_COST_MULTIPLIER = {
    "common": 1.0,
    "rare": 1.6,
    "epic": 2.6,
    "legendary": 4.0,
}

BASE_UPGRADE_COST = {
    "gold": 500,
    "elixir": 100,
    "shiny_ore": 2,
}

EPIC_EXTRA_COST = {
    "glowy_ore": 1,
}

LEGENDARY_EXTRA_COST = {
    "dark_elixir": 25,
    "glowy_ore": 2,
    "starry_ore": 1,
}


def get_upgrade_level(item: dict) -> int:
    return max(0, int(item.get("upgrade_level", item.get("plus", 0)) or 0))


def get_display_name(base_name: str, upgrade_level: int) -> str:
    upgrade_level = max(0, int(upgrade_level or 0))
    if upgrade_level <= 0:
        return base_name
    return f"{base_name} +{upgrade_level}"


def get_next_upgrade_cost(rarity: str, current_level: int) -> dict:
    rarity = str(rarity or "common").lower()
    current_level = max(0, int(current_level or 0))
    next_level = current_level + 1

    if next_level > MAX_GEAR_UPGRADE_LEVEL:
        return {}

    rarity_multiplier = float(RARITY_COST_MULTIPLIER.get(rarity, 1.0))
    level_multiplier = next_level * next_level

    cost = {
        currency: max(1, int(amount * rarity_multiplier * level_multiplier))
        for currency, amount in BASE_UPGRADE_COST.items()
    }

    if rarity in {"epic", "legendary"}:
        for currency, amount in EPIC_EXTRA_COST.items():
            cost[currency] = cost.get(currency, 0) + max(1, int(amount * level_multiplier))

    if rarity == "legendary":
        for currency, amount in LEGENDARY_EXTRA_COST.items():
            cost[currency] = cost.get(currency, 0) + max(1, int(amount * level_multiplier))

    return cost


def get_stat_multiplier(upgrade_level: int) -> float:
    upgrade_level = max(0, int(upgrade_level or 0))
    return 1 + (upgrade_level * 0.08)
