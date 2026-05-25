from __future__ import annotations

from .phases import get_boss_phase



def format_raid_status(raid: dict):
    phase = get_boss_phase(raid)

    return (
        f"Boss: {raid['boss_name']}\n"
        f"Health: {raid['health']:,}/{raid['max_health']:,}\n"
        f"Phase: {phase}\n"
        f"Raiders: {len(raid['players'])}"
    )



def format_attack_result(result: dict):
    return (
        f"Damage: {result['damage']:,}\n"
        f"Boss HP: {result['boss_health']:,}\n"
        f"Boss Ability: {result['boss_ability']}\n"
        f"Gold: {result['rewards']['gold']:,}\n"
        f"Gems: {result['rewards']['gems']:,}"
    )