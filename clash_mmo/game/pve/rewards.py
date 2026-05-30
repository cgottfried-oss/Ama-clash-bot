from __future__ import annotations

from clash_mmo.game.pve.bosses import get_boss
from clash_mmo.game.pve.chests import get_chest_rewards


RESOURCE_NAMES = {
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


def calculate_boss_rewards(boss_id: str) -> dict:
    boss = get_boss(boss_id)
    rewards = boss.get("base_rewards", {}) if boss else {}
    return dict(rewards) if isinstance(rewards, dict) else {}


def merge_rewards(*reward_sets: dict) -> dict:
    merged = {}
    for rewards in reward_sets:
        for resource, amount in (rewards or {}).items():
            merged[resource] = int(merged.get(resource, 0) or 0) + int(amount or 0)
    return {resource: amount for resource, amount in merged.items() if amount}


def calculate_participant_rewards(instance: dict, user_id: str) -> dict:
    participants = instance.get("participants", {}) or {}
    participant = participants.get(str(user_id), {}) or {}
    total_damage = sum(int((data or {}).get("damage", 0) or 0) for data in participants.values())
    user_damage = int(participant.get("damage", 0) or 0)
    base_rewards = instance.get("rewards", {}) or {}
    if total_damage <= 0 or user_damage <= 0:
        return {}
    share_pct = max(5, min(100, user_damage * 100 // total_damage))
    return {resource: max(1, int(amount or 0) * share_pct // 100) for resource, amount in base_rewards.items()}


def add_chest_rewards(rewards: dict, chest_id: str) -> dict:
    return merge_rewards(rewards, get_chest_rewards(chest_id))


def format_rewards(rewards: dict) -> str:
    if not rewards:
        return "None"
    return ", ".join(f"{int(amount):,} {RESOURCE_NAMES.get(resource, resource.replace('_', ' ').title())}" for resource, amount in rewards.items())
