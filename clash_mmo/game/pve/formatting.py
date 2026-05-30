from __future__ import annotations

from clash_mmo.game.pve.bosses import boss_name
from clash_mmo.game.pve.rewards import format_rewards


def format_boss_status(instance: dict) -> str:
    boss_id = instance.get("boss_id", "unknown")
    hp = int(instance.get("hp", 0) or 0)
    max_hp = int(instance.get("max_hp", 1) or 1)
    phase = int(instance.get("phase", 1) or 1)
    percent = max(0, min(100, hp * 100 // max_hp))
    return f"**{boss_name(boss_id)}** — HP: **{hp:,}/{max_hp:,}** ({percent}%) — Phase **{phase}**"


def format_participants(instance: dict) -> str:
    participants = instance.get("participants", {}) or {}
    if not participants:
        return "No participants yet."
    lines = []
    for user_id, data in participants.items():
        damage = int((data or {}).get("damage", 0) or 0)
        lines.append(f"<@{user_id}> — **{damage:,}** damage")
    return "\n".join(lines[:15])


def format_instance_summary(instance: dict) -> str:
    rewards = instance.get("rewards", {}) or {}
    return f"{format_boss_status(instance)}\nRewards: {format_rewards(rewards)}\n\n{format_participants(instance)}"
