from __future__ import annotations



def get_region_owner(state: dict, region_id: str):
    territories = state.setdefault("territories", {})
    region = territories.setdefault(region_id, {})

    return region.get("owner")



def claim_region(state: dict, region_id: str, clan_id: str):
    territories = state.setdefault("territories", {})

    territories.setdefault(region_id, {})
    territories[region_id]["owner"] = clan_id

    return territories[region_id]



def release_region(state: dict, region_id: str):
    territories = state.setdefault("territories", {})

    if region_id not in territories:
        return False

    territories[region_id]["owner"] = None
    return True
