from __future__ import annotations

CHEST_TIERS = {
    "common": {
        "name": "Common Chest",
        "emoji": "📦",
        "weight": 70,
        "rewards": {"gold": 500, "elixir": 250},
    },
    "rare": {
        "name": "Rare Chest",
        "emoji": "🎁",
        "weight": 25,
        "rewards": {"gold": 1000, "elixir": 500, "shiny_ore": 10},
    },
    "legendary": {
        "name": "Legendary Chest",
        "emoji": "🏆",
        "weight": 5,
        "rewards": {"gold": 2500, "gems": 5, "glowy_ore": 8, "starry_ore": 2},
    },
}


def chest_display_name(chest_id: str) -> str:
    chest = CHEST_TIERS.get(chest_id, {})
    return f"{chest.get('emoji', '📦')} {chest.get('name', str(chest_id).replace('_', ' ').title())}"


def get_chest_rewards(chest_id: str) -> dict:
    chest = CHEST_TIERS.get(chest_id, {})
    rewards = chest.get("rewards", {})
    return dict(rewards) if isinstance(rewards, dict) else {}
