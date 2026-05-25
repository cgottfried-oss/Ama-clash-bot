from __future__ import annotations

import random


BOSS_ABILITIES = [
    "Meteor Slam",
    "Void Pulse",
    "Infernal Breath",
    "Crystal Barrage",
    "Titan Shockwave",
]



def roll_boss_ability():
    return random.choice(BOSS_ABILITIES)
