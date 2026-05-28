from __future__ import annotations

import random

from .abilities import roll_boss_ability
from .instances import create_raid_instance
from .bosses import RAID_BOSSES
from .rewards import calculate_boss_defeat_rewards
from .windows import open_damage_window
from .equipment.service import get_effective_profile_stats
from .raid_damage import calculate_raid_damage



def start_raid(state: dict, boss_id: str):
    raid = create_raid_instance(boss_id)
    raid["damage_window"] = open_damage_window()

    state["active_raid"] = raid

    return raid



def join_raid(raid: dict, user_id: str):
    if user_id not in raid["players"]:
        raid["players"].append(user_id)

    return raid



def attack_raid_boss(raid: dict, profile: dict):
    stats = get_effective_profile_stats(profile)

    damage_roll = calculate_raid_damage(profile)
    raw_damage = int(damage_roll["damage"])
    boss_ability = roll_boss_ability()
    ability_damage_multiplier = 1.0
    cooldown_penalty_seconds = 0

    if boss_ability:
        ability_damage_multiplier = float(boss_ability.get("damage_multiplier", 1.0) or 1.0)
        cooldown_penalty_seconds = int(boss_ability.get("cooldown_penalty_seconds", 0) or 0)

    damage = max(1, int(raw_damage * ability_damage_multiplier))

    user_id = profile["identity"]["user_id"]

    raid.setdefault("players", [])
    raid.setdefault("damage", {})
    raid.setdefault("rewards_claimed", False)
    raid.setdefault("mechanics", {})

    if user_id not in raid["players"]:
        raid["players"].append(user_id)

    raid["health"] = max(0, int(raid.get("health", 0) or 0) - damage)

    raid["damage"].setdefault(user_id, 0)
    raid["damage"][user_id] += damage

    if boss_ability:
        mechanics = raid.setdefault("mechanics", {})
        user_mechanics = mechanics.setdefault(user_id, {})
        user_mechanics["last_ability"] = boss_ability["id"]
        user_mechanics["last_ability_name"] = boss_ability["name"]
        user_mechanics["cooldown_penalty_seconds"] = cooldown_penalty_seconds

    boss_defeated = raid["health"] <= 0
    if boss_defeated:
        raid["active"] = False
        raid["defeated"] = True

    boss_id = raid.get("boss_id")
    boss_data = RAID_BOSSES.get(boss_id, {})
    boss_rarity = boss_data.get("rarity", "epic")

    defeat_rewards = None
    if boss_defeated and not raid.get("rewards_claimed"):
        total_damage = sum(int(value or 0) for value in raid.get("damage", {}).values()) or 1
        defeat_rewards = {}

        for participant_id, participant_damage in raid.get("damage", {}).items():
            active_hero = None

            if str(participant_id) == str(user_id):
                active_hero = profile.get("active_hero")

            defeat_rewards[participant_id] = calculate_boss_defeat_rewards(
                player_damage=int(participant_damage or 0),
                total_damage=total_damage,
                boss_rarity=boss_rarity,
                active_hero=active_hero,
            )

        raid["rewards_claimed"] = True

    return {
        "damage": damage,
        "raw_damage": raw_damage,
        "boss_health": raid["health"],
        "boss_max_health": raid.get("max_health", 0),
        "boss_ability": boss_ability,
        "cooldown_penalty_seconds": cooldown_penalty_seconds,
        "boss_defeated": boss_defeated,
        "defeat_rewards": defeat_rewards,
    }