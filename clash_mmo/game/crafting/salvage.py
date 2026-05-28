from __future__ import annotations

SALVAGE_REWARDS = {
    "common": {
        "gold": 250,
        "elixir": 25,
    },
    "rare": {
        "gold": 500,
        "elixir": 75,
        "shiny_ore": 2,
    },
    "epic": {
        "gold": 1000,
        "elixir": 150,
        "shiny_ore": 5,
        "glowy_ore": 1,
    },
    "legendary": {
        "gold": 2500,
        "elixir": 300,
        "dark_elixir": 50,
        "shiny_ore": 10,
        "glowy_ore": 3,
        "starry_ore": 1,
    },
}


DEFAULT_REWARD = {
    "gold": 100,
}



def get_salvage_rewards(rarity: str) -> dict:
    rarity = str(rarity or "common").strip().lower()
    rewards = SALVAGE_REWARDS.get(rarity, DEFAULT_REWARD)
    return dict(rewards)
