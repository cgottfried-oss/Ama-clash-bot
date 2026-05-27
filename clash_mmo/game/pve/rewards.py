from __future__ import annotations

import random

def calculate_boss_defeat_rewards(
    *,
    player_damage: int,
    total_damage: int,
    boss_rarity: str = "epic",
):
    player_damage = max(0, int(player_damage or 0))
    total_damage = max(1, int(total_damage or 1))

    share = player_damage / total_damage

    rarity_multiplier = {
        "common": 1.0,
        "rare": 1.15,
        "epic": 1.35,
        "legendary": 1.65,
    }.get(str(boss_rarity).lower(), 1.25)

    gold = int((900 + player_damage * 1.4 + share * 4500) * rarity_multiplier)
    gems = int(1 + share * 5)

    if boss_rarity == "legendary":
        gems += 1

    medals = max(1, int(1 + share * 6))
    clan_xp = int((45 + share * 240) * rarity_multiplier)

    legend_chest_chance = {
        "common": 0.00,
        "rare": 0.03,
        "epic": 0.06,
        "legendary": 0.10,
    }.get(str(boss_rarity).lower(), 0.05)

    legend_chest = random.random() < legend_chest_chance

    return {
        "gold": gold,
        "gems": gems,
        "medals": medals,
        "clan_xp": clan_xp,
        "legend_chest": legend_chest,
        "legend_chest_chance": legend_chest_chance,
        "share": share,
    }