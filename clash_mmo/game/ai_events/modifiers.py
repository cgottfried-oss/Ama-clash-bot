from __future__ import annotations

import random


EVENT_MODIFIERS = [
    {
        "name": "Double Rewards",
        "effect": "reward_multiplier",
        "value": 2,
    },
    {
        "name": "Market Inflation",
        "effect": "market_tax_bonus",
        "value": 0.10,
    },
    {
        "name": "Raid Frenzy",
        "effect": "raid_damage_bonus",
        "value": 1.5,
    },
    {
        "name": "Conquest Rush",
        "effect": "territory_points_bonus",
        "value": 2,
    },
]



def pick_event_modifier():
    return random.choice(EVENT_MODIFIERS)