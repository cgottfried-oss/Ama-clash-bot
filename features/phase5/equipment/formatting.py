from __future__ import annotations

from .gear_catalog import GEAR_CATALOG
from .heroes import HERO_CATALOG



def format_gear_line(item: dict):
    gear = GEAR_CATALOG.get(item.get("item_id"), {})

    return (
        f"**{gear.get('name', item.get('item_id'))}** "
        f"[{item.get('rarity', 'common').title()}]"
    )



def format_stats_block(stats: dict):
    lines = []

    for stat, value in stats.items():
        lines.append(f"**{stat.title()}**: {round(value, 2)}")

    return "\n".join(lines)



def format_hero_line(hero_id: str, hero_data: dict):
    hero = HERO_CATALOG.get(hero_id, {})

    return (
        f"🦸 **{hero.get('name', hero_id)}** "
        f"Lv.{hero_data.get('level', 1)}"
    )
