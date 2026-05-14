from __future__ import annotations

import json
from hashlib import sha256


def serialize_plan(plan) -> dict:
    payload = {
        "schema": "ama_base_blueprint_v1",
        "townhall": plan.townhall,
        "style": plan.style,
        "anti_meta": plan.anti_meta,
        "symmetry": plan.symmetry,
        "title": plan.title,
        "placements": getattr(plan, "placements", []),
        "walls": getattr(plan, "walls", []),
        "compartments": getattr(plan, "compartments", []),
        "placement_guide": getattr(plan, "placement_guide", []),
        "trap_plan": plan.trap_plan,
        "rules": plan.rules,
        "notes": plan.notes,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["layout_hash"] = sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return payload


def serialize_plan_json(plan) -> str:
    return json.dumps(serialize_plan(plan), indent=2, sort_keys=True)


def share_link_status() -> dict:
    return {
        "status": "research_required",
        "can_generate_official_link": False,
        "reason": "Supercell does not expose a public API for creating official layout import tokens from arbitrary coordinates.",
        "next_step": "Collect multiple official Clash layout links with tiny layout differences and compare them with /baselab_compare.",
    }
