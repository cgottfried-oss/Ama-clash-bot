from __future__ import annotations

from clash_mmo.game.equipment.abilities import ability_display_name
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG


def rarity_emoji(rarity: str) -> str:
    return {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
    }.get(str(rarity).lower(), "⚪")


def gear_display_name(item_id: str) -> str:
    item = GEAR_CATALOG.get(item_id, {})
    return item.get("name", str(item_id).replace("_", " ").title())


def format_gear_item(item: dict) -> str:
    item_id = item.get("item_id") or item.get("id") or "unknown"
    catalog = GEAR_CATALOG.get(item_id, {})
    rarity = item.get("rarity") or catalog.get("rarity", "common")
    slot = item.get("slot") or catalog.get("slot", "unknown")
    hero = item.get("hero") or catalog.get("hero", "any")
    ability = item.get("ability") or catalog.get("ability")
    ability_text = f" • Ability: **{ability_display_name(ability)}**" if ability else ""
    return f"{rarity_emoji(rarity)} **{gear_display_name(item_id)}** — {str(rarity).title()} {str(slot).title()} • Hero: {str(hero).replace('_', ' ').title()}{ability_text}"


def format_gear_list(items: list[dict]) -> str:
    if not items:
        return "No gear owned."
    return "\n".join(format_gear_item(item) for item in items[:15])
