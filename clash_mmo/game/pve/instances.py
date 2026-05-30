from __future__ import annotations

import time
import uuid

from clash_mmo.game.pve.bosses import get_boss
from clash_mmo.game.pve.rewards import calculate_boss_rewards


def create_pve_instance(boss_id: str, created_by: str, now: int | None = None) -> dict:
    now = int(now or time.time())
    boss = get_boss(boss_id)
    if not boss:
        raise ValueError(f"Unknown boss: {boss_id}")
    max_hp = int(boss.get("max_hp", 1) or 1)
    return {
        "instance_id": f"pve-{uuid.uuid4().hex[:10]}",
        "boss_id": boss_id,
        "created_by": str(created_by),
        "created_at": now,
        "status": "active",
        "hp": max_hp,
        "max_hp": max_hp,
        "phase": 1,
        "phase_count": int(boss.get("phase_count", 1) or 1),
        "participants": {},
        "rewards": calculate_boss_rewards(boss_id),
        "events": [],
    }


def ensure_pve_state(state: dict) -> dict:
    pve = state.setdefault("pve", {})
    if not isinstance(pve, dict):
        pve = {}
        state["pve"] = pve
    pve.setdefault("instances", {})
    pve.setdefault("history", [])
    return pve


def get_active_instance(state: dict, instance_id: str | None = None) -> dict | None:
    pve = ensure_pve_state(state)
    instances = pve.setdefault("instances", {})
    if instance_id:
        instance = instances.get(instance_id)
        if instance and instance.get("status") == "active":
            return instance
        return None
    for instance in instances.values():
        if isinstance(instance, dict) and instance.get("status") == "active":
            return instance
    return None
