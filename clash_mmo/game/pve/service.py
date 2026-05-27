from __future__ import annotations

import random

from .abilities import roll_boss_ability
from .instances import create_raid_instance
from .bosses import RAID_BOSSES
from .rewards import calculate_raid_rewards, calculate_boss_defeat_rewards
from .windows import open_damage_window
from ..equipment.service import get_effective_profile_stats



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

    damage = int(
        (
            float(stats.get("attack", 0)) * random.uniform(1.0, 2.2)
        ) + (
            float(stats.get("crit", 0)) * 100
        )
    )

    user_id = profile["identity"]["user_id"]

    raid.setdefault("players", [])
    raid.setdefault("damage", {})
    raid.setdefault("rewards_claimed", False)

    if user_id not in raid["players"]:
        raid["players"].append(user_id)

    raid["health"] = max(0, int(raid.get("health", 0) or 0) - damage)

    raid["damage"].setdefault(user_id, 0)
    raid["damage"][user_id] += damage

    boss_defeated = raid["health"] <= 0
    if boss_defeated:
        raid["active"] = False
        raid["defeated"] = True

    rewards = calculate_raid_rewards(damage)

    boss_id = raid.get("boss_id")
    boss_data = RAID_BOSSES.get(boss_id, {})
    boss_rarity = boss_data.get("rarity", "epic")

    defeat_rewards = None
    if boss_defeated and not raid.get("rewards_claimed"):
        total_damage = sum(int(value or 0) for value in raid.get("damage", {}).values()) or 1
        defeat_rewards = {}

        for participant_id, participant_damage in raid.get("damage", {}).items():
            defeat_rewards[participant_id] = calculate_boss_defeat_rewards(
                player_damage=int(participant_damage or 0),
                total_damage=total_damage,
                boss_rarity=boss_rarity,
            )

        raid["rewards_claimed"] = True

    return {
        "damage": damage,
        "boss_health": raid["health"],
        "boss_ability": roll_boss_ability(),
        "rewards": rewards,
        "boss_defeated": boss_defeated,
        "defeat_rewards": defeat_rewards,
    }