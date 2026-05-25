from __future__ import annotations

import random

from .abilities import roll_boss_ability
from .instances import create_raid_instance
from .rewards import calculate_raid_rewards
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
            float(stats.get("crit", 0)) * 100)
    )

    raid["health"] = max(0, raid["health"] - damage)

    user_id = profile["identity"]["user_id"]

    raid["damage"].setdefault(user_id, 0)
    raid["damage"][user_id] += damage

    rewards = calculate_raid_rewards(damage)

    return {
        "damage": damage,
        "boss_health": raid["health"],
        "boss_ability": roll_boss_ability(),
        "rewards": rewards,
        "boss_defeated": raid["health"] <= 0,
    }
