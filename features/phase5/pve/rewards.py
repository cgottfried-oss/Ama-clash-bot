from __future__ import annotations



def calculate_raid_rewards(total_damage: int):
    gold = max(500, total_damage * 2)
    gems = max(5, total_damage // 1000)

    return {
        "gold": gold,
        "gems": gems,
    }
