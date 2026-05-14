from __future__ import annotations

from .generator import BasePlan


def score_base(plan: BasePlan) -> dict:
    score = 100
    findings = []
    recommendations = []

    if plan.anti_meta == "fireball":
        findings.append("Major defenses appear intentionally spread for reduced Fireball value.")
        score += 8
    else:
        recommendations.append("Increase spacing between premium defenses to reduce Fireball value.")
        score -= 4

    if plan.anti_meta == "root_rider":
        findings.append("Core pathing appears intentionally broken to slow Root Riders.")
        score += 10
    else:
        recommendations.append("Add more disconnected compartments to disrupt Root Rider pathing.")
        score -= 5

    if plan.symmetry == "box":
        findings.append("Box symmetry provides predictable but sturdy compartment structure.")
    elif plan.symmetry == "ring":
        findings.append("Ring-style pathing can punish impatient smash attacks.")
        score += 3
    elif plan.symmetry == "diamond":
        findings.append("Diamond core can create awkward funneling for meta attacks.")
        score += 2
    else:
        recommendations.append("Pure random symmetry can become inconsistent without testing.")

    if plan.style == "war":
        score += 5
    elif plan.style == "legend":
        score += 2

    vulnerabilities = {
        "fireball_value": max(1, 10 - (score // 15)),
        "root_rider_pathing": max(1, 10 - (score // 14)),
        "blimp_access": max(1, 10 - (score // 13)),
        "queen_charge_value": max(1, 10 - (score // 16)),
    }

    return {
        "overall_score": max(1, min(score, 100)),
        "findings": findings,
        "recommendations": recommendations,
        "vulnerabilities": vulnerabilities,
    }
