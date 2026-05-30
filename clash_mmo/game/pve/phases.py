from __future__ import annotations


def calculate_phase(instance: dict) -> int:
    hp = int(instance.get("hp", 0) or 0)
    max_hp = max(1, int(instance.get("max_hp", 1) or 1))
    phase_count = max(1, int(instance.get("phase_count", 1) or 1))
    missing_pct = max(0, min(100, 100 - (hp * 100 // max_hp)))
    phase = min(phase_count, 1 + (missing_pct * phase_count // 100))
    return max(1, phase)


def update_phase(instance: dict) -> int:
    old_phase = int(instance.get("phase", 1) or 1)
    new_phase = calculate_phase(instance)
    instance["phase"] = new_phase
    if new_phase > old_phase:
        instance.setdefault("events", []).append({"type": "phase_change", "phase": new_phase})
    return new_phase
