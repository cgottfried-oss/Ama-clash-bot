from __future__ import annotations

from typing import Any


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def ensure_player_profile(state: dict, user_id: str, name: str = "Unknown") -> dict:
    players = state.setdefault("players", {})
    user_id = str(user_id)

    profile = players.setdefault(user_id, {})
    profile.setdefault("user_id", user_id)
    profile.setdefault("name", name or "Unknown")
    profile.setdefault("identity", {})
    profile["identity"].setdefault("display_name", name or profile.get("name", "Unknown"))

    profile["gold"] = max(0, _int(profile.get("gold", 0)))
    profile["elixir"] = max(0, _int(profile.get("elixir", 0)))
    profile["dark_elixir"] = max(0, _int(profile.get("dark_elixir", 0)))
    profile["gems"] = max(0, _int(profile.get("gems", 0)))
    profile["raid_medals"] = max(0, _int(profile.get("raid_medals", 0)))
    profile["clan_xp"] = max(0, _int(profile.get("clan_xp", 0)))
    profile["shiny_ore"] = max(0, _int(profile.get("shiny_ore", 0)))
    profile["glowy_ore"] = max(0, _int(profile.get("glowy_ore", 0)))
    profile["starry_ore"] = max(0, _int(profile.get("starry_ore", 0)))
    profile["town_hall"] = max(1, _int(profile.get("town_hall", 1), 1))

    profile.setdefault("daily_streak", 0)
    profile.setdefault("cooldowns", {})
    profile.setdefault("boosts", {})
    profile.setdefault("stats", {})
    profile.setdefault("achievements", [])
    profile.setdefault("inventory", {})
    profile.setdefault("shop_inventory", {})
    profile.setdefault("heroes", {})
    profile.setdefault("active_hero", None)
    profile.setdefault("pvp", {})
    profile.setdefault("season", {})
    profile.setdefault("cosmetics", {})
    profile.setdefault("equipped_cosmetics", {})

    inventory = profile.setdefault("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
        profile["inventory"] = inventory
    inventory.setdefault("items", [])
    inventory.setdefault("materials", {})

    if not isinstance(profile.get("shop_inventory"), dict):
        profile["shop_inventory"] = {}
    if not isinstance(profile.get("heroes"), dict):
        profile["heroes"] = {}
    if not isinstance(profile.get("cooldowns"), dict):
        profile["cooldowns"] = {}
    if not isinstance(profile.get("boosts"), dict):
        profile["boosts"] = {}
    if not isinstance(profile.get("stats"), dict):
        profile["stats"] = {}
    if not isinstance(profile.get("pvp"), dict):
        profile["pvp"] = {}

    players[user_id] = profile
    return profile
