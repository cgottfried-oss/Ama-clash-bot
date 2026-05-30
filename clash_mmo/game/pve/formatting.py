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
    lines = [
        f"💥 Damage Dealt: **{result['damage']:,}**",
        f"❤️ Boss HP: **{result['boss_health']:,}/{result.get('boss_max_health', 0):,}**",
        "",
        "🏅 Raid contribution recorded.",
    ]

    ability = result.get("boss_ability")

    if ability:
        lines.extend([
            "",
            f"⚡ **{ability['name']} triggered!**",
            ability.get("description", "The boss retaliated."),
        ])

        cooldown_penalty = int(result.get("cooldown_penalty_seconds", 0) or 0)

        if cooldown_penalty:
            minutes = max(1, cooldown_penalty // 60)
            lines.append(f"⏳ Raid fatigue added: **+{minutes} min** to your next raid attack window.")

        raw_damage = int(result.get("raw_damage", result["damage"]) or result["damage"])
        damage = int(result["damage"])

        if damage < raw_damage:
            lost = raw_damage - damage
            lines.append(f"🛡️ Damage reduced by boss mechanics: **-{lost:,}**.")

    if result.get("boss_defeated"):
        lines.extend([
            "",
            "🏆 **Boss defeated!** Rewards are paid based on total contribution.",
        ])

    return "\n".join(lines)