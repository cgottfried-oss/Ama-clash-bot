from __future__ import annotations

import random


BOSS_ABILITIES = [
    {
        "id": "meteor_slam",
        "name": "Meteor Slam",
        "description": "The boss slams the battlefield, reducing your damage this attack.",
        "trigger_chance": 0.22,
        "damage_multiplier": 0.75,
        "cooldown_penalty_seconds": 0,
    },
    {
        "id": "void_pulse",
        "name": "Void Pulse",
        "description": "Void energy disrupts your army and adds raid fatigue.",
        "trigger_chance": 0.18,
        "damage_multiplier": 0.90,
        "cooldown_penalty_seconds": 120,
    },
    {
        "id": "infernal_breath",
        "name": "Infernal Breath",
        "description": "Infernal flames burn through your push, cutting damage hard.",
        "trigger_chance": 0.16,
        "damage_multiplier": 0.65,
        "cooldown_penalty_seconds": 0,
    },
    {
        "id": "crystal_barrage",
        "name": "Crystal Barrage",
        "description": "Crystal shards scatter your troops, slightly reducing damage.",
        "trigger_chance": 0.20,
        "damage_multiplier": 0.85,
        "cooldown_penalty_seconds": 60,
    },
    {
        "id": "titan_shockwave",
        "name": "Titan Shockwave",
        "description": "A massive shockwave delays your next attack window.",
        "trigger_chance": 0.15,
        "damage_multiplier": 1.00,
        "cooldown_penalty_seconds": 180,
    },
]


def roll_boss_ability():
    ability = random.choice(BOSS_ABILITIES)

    if random.random() > float(ability.get("trigger_chance", 0) or 0):
        return None

    return ability