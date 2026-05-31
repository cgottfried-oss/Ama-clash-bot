from __future__ import annotations

import random

from .regions import TERRITORY_REGIONS
from .conquest import resolve_conquest


# NPC raider bands periodically attack owned territories. Each owned region's
# fortification (its accumulated conquest_points) defends it. If the NPC wins,
# the region is lost — its owner is cleared and some conquest points are
# stripped. This creates "defend or lose it" pressure so claiming isn't
# permanent and players stay engaged.

# Tunable: NPC attack power scales with the region's tier (higher-value
# regions draw stronger raiders), plus a random band size.
NPC_BASE_POWER = 40
NPC_TIER_SCALING = 12
NPC_RANDOM_SPREAD = (0.8, 1.3)

# On a successful NPC capture, this fraction of the region's conquest points
# is stripped (the rest represents surviving fortifications the clan can rebuild).
CONQUEST_LOSS_ON_CAPTURE = 0.5


def _region_fortification(region_data: dict) -> float:
    # Defender power is the region's conquest points (fortification) plus a
    # small baseline so a freshly-claimed region isn't a free NPC win.
    pts = int(region_data.get("conquest_points", 0) or 0)
    return 30 + min(pts, 600)


def _npc_power_for_tier(tier: int) -> float:
    base = NPC_BASE_POWER + tier * NPC_TIER_SCALING
    return base * random.uniform(*NPC_RANDOM_SPREAD)


def run_npc_territory_raids(state: dict):
    """Roll an NPC raid against each currently-owned territory.

    Returns a list of result dicts describing what happened, so the caller
    (the loop in bot_runner) can announce captures in the channel.
    """
    if not isinstance(state, dict):
        return []

    territories = state.setdefault("territories", {})
    results = []

    for region_id, region_meta in TERRITORY_REGIONS.items():
        region_data = territories.get(region_id)
        if not isinstance(region_data, dict):
            continue

        owner = region_data.get("owner")
        if not owner:
            continue  # unowned regions aren't attacked

        tier = int(region_meta.get("tier", 1) or 1)
        npc_power = _npc_power_for_tier(tier)
        defender_power = _region_fortification(region_data)

        outcome = resolve_conquest(attacker_power=npc_power, defender_power=defender_power)

        if outcome["attacker_won"]:
            # NPC captures the region: clear owner, strip half the conquest pts.
            current_pts = int(region_data.get("conquest_points", 0) or 0)
            region_data["owner"] = None
            region_data["conquest_points"] = int(current_pts * (1 - CONQUEST_LOSS_ON_CAPTURE))
            results.append({
                "region_id": region_id,
                "region_name": region_meta.get("name", region_id),
                "previous_owner": owner,
                "captured": True,
                "npc_power": round(npc_power, 1),
                "defense_power": round(defender_power, 1),
            })
        else:
            results.append({
                "region_id": region_id,
                "region_name": region_meta.get("name", region_id),
                "previous_owner": owner,
                "captured": False,
                "npc_power": round(npc_power, 1),
                "defense_power": round(defender_power, 1),
            })

    return results
