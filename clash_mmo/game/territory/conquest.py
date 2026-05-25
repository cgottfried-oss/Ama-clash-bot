from __future__ import annotations

import random



def resolve_conquest(attacker_power: float, defender_power: float):
    attack_roll = attacker_power * random.uniform(0.85, 1.2)
    defense_roll = defender_power * random.uniform(0.85, 1.2)

    attacker_won = attack_roll >= defense_roll

    return {
        "attacker_won": attacker_won,
        "attack_roll": round(attack_roll, 2),
        "defense_roll": round(defense_roll, 2),
    }
