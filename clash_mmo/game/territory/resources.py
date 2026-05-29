from __future__ import annotations

from clash_mmo.game.territory.regions import TERRITORY_REGIONS


def get_region_income(region_id: str) -> dict:
    region = TERRITORY_REGIONS.get(region_id, {})
    income = region.get("base_income", {})
    if not isinstance(income, dict):
        return {}
    return {str(resource): int(amount or 0) for resource, amount in income.items()}


def apply_resource_delta(profile: dict, rewards: dict) -> dict:
    granted = {}
    for resource, amount in (rewards or {}).items():
        amount = int(amount or 0)
        if amount == 0:
            continue
        profile[resource] = max(0, int(profile.get(resource, 0) or 0) + amount)
        granted[resource] = granted.get(resource, 0) + amount
    return granted


def format_resource_bundle(resources: dict) -> str:
    if not resources:
        return "None"
    names = {
        "gold": "Gold",
        "elixir": "Elixir",
        "dark_elixir": "Dark Elixir",
        "gems": "Gems",
        "raid_medals": "Raid Medals",
        "clan_xp": "Clan XP",
        "shiny_ore": "Shiny Ore",
        "glowy_ore": "Glowy Ore",
        "starry_ore": "Starry Ore",
    }
    return ", ".join(f"{int(amount):,} {names.get(resource, resource.replace('_', ' ').title())}" for resource, amount in resources.items())
