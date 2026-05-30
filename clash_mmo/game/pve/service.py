from __future__ import annotations

import time

from clash_mmo.game.pve.instances import create_pve_instance, ensure_pve_state, get_active_instance
from clash_mmo.game.pve.raid_damage import apply_raid_damage, calculate_raid_damage
from clash_mmo.game.pve.rewards import calculate_participant_rewards


def start_pve_raid(state: dict, boss_id: str, created_by: str, now: int | None = None) -> dict:
    pve = ensure_pve_state(state)
    instance = create_pve_instance(boss_id, created_by, now=now)
    pve.setdefault("instances", {})[instance["instance_id"]] = instance
    return instance


def join_pve_raid(state: dict, user_id: str, instance_id: str | None = None) -> tuple[bool, dict | None]:
    instance = get_active_instance(state, instance_id)
    if not instance:
        return False, None
    participants = instance.setdefault("participants", {})
    participants.setdefault(str(user_id), {"damage": 0, "joined_at": int(time.time())})
    return True, instance


def attack_pve_raid(state: dict, user_id: str, profile: dict, instance_id: str | None = None, base_damage: int = 100) -> tuple[bool, dict | None, int]:
    instance = get_active_instance(state, instance_id)
    if not instance:
        return False, None, 0
    damage = calculate_raid_damage(profile, base_damage=base_damage)
    apply_raid_damage(instance, str(user_id), damage)
    return True, instance, damage


def claim_pve_rewards(state: dict, user_id: str, instance_id: str) -> dict:
    pve = ensure_pve_state(state)
    instance = pve.setdefault("instances", {}).get(instance_id)
    if not instance or instance.get("status") != "defeated":
        return {}
    participants = instance.setdefault("participants", {})
    participant = participants.setdefault(str(user_id), {"damage": 0})
    if participant.get("claimed"):
        return {}
    rewards = calculate_participant_rewards(instance, str(user_id))
    participant["claimed"] = True
    participant["claimed_rewards"] = rewards
    return rewards
