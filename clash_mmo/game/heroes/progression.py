from __future__ import annotations

from clash_mmo.game.heroes.catalog import get_hero_config



def get_hero_upgrade_cost(hero_id: str, current_level: int) -> dict:
    hero_id = str(hero_id or "").strip().lower()
    current_level = max(1, int(current_level or 1))

    config = get_hero_config(hero_id)

    if not config:
        return {
            "gold": 999_999_999,
            "dark_elixir": 999_999_999,
            "clan_xp": 999_999_999,
        }

    base_gold = int(config.get("base_upgrade_gold", 1_500) or 1_500)
    base_dark_elixir = int(config.get("base_upgrade_dark_elixir", 75) or 75)
    base_clan_xp = int(config.get("base_upgrade_clan_xp", 100) or 100)

    multiplier = current_level + 1

    return {
        "gold": int(base_gold * multiplier * 1.15),
        "dark_elixir": int(base_dark_elixir * multiplier * 1.18),
        "clan_xp": int(base_clan_xp * multiplier * 1.10),
    }
