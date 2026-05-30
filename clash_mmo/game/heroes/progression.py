from __future__ import annotations

from clash_mmo.game.heroes.catalog import get_hero_config

MAX_HERO_LEVEL = 10

HERO_DARK_ELIXIR_COSTS = {
    1: 100,
    2: 175,
    3: 275,
    4: 400,
    5: 575,
    6: 775,
    7: 1000,
    8: 1300,
    9: 1650,
}


def get_max_hero_level() -> int:
    return MAX_HERO_LEVEL


def get_hero_upgrade_cost(hero_id: str, current_level: int) -> dict:
    hero_id = str(hero_id or "").strip().lower()
    current_level = max(1, int(current_level or 1))

    config = get_hero_config(hero_id)

    if not config:
        return {"dark_elixir": 999_999_999}

    if current_level >= MAX_HERO_LEVEL:
        return {"dark_elixir": 0}

    return {
        "dark_elixir": int(HERO_DARK_ELIXIR_COSTS.get(current_level, 999_999_999)),
    }
