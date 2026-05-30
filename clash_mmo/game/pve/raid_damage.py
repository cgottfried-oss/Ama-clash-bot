from __future__ import annotations

from clash_mmo.game.pve.phases import update_phase


def calculate_raid_damage(profile: dict, base_damage: int = 100) -> int:
    town_hall = int(profile.get("town_hall", 1) or 1)
    clan_xp = int(profile.get("clan_xp", 0) or 0)
    hero_power = int(profile.get("hero_power", 0) or 0)
    return max(1, int(base_damage) + (town_hall * 25) + min(clan_xp, 5000) // 25 + hero_power)


def apply_raid_damage(instance: dict, user_id: str, damage: int) -> dict:
    damage = max(0, int(damage or 0))
    instance["hp"] = max(0, int(instance.get("hp", 0) or 0) - damage)
    participants = instance.setdefault("participants", {})
    participant = participants.setdefault(str(user_id), {"damage": 0})
    participant["damage"] = int(participant.get("damage", 0) or 0) + damage
    update_phase(instance)
    if instance["hp"] <= 0:
        instance["status"] = "defeated"
    return participant
