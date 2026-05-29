from __future__ import annotations

PVE_ABILITIES = {
    "power_strike": {
        "name": "Power Strike",
        "description": "Deal bonus damage to the current boss.",
        "cooldown_seconds": 60,
        "damage_multiplier": 1.35,
    },
    "shield_wall": {
        "name": "Shield Wall",
        "description": "Reduce incoming phase damage for the party.",
        "cooldown_seconds": 120,
        "damage_reduction_pct": 15,
    },
    "rally": {
        "name": "Rally",
        "description": "Boost party damage for the next window.",
        "cooldown_seconds": 180,
        "party_damage_bonus_pct": 10,
    },
}


def ability_name(ability_id: str) -> str:
    return PVE_ABILITIES.get(ability_id, {}).get("name", str(ability_id).replace("_", " ").title())


def get_ability(ability_id: str) -> dict:
    return dict(PVE_ABILITIES.get(ability_id, {}))
