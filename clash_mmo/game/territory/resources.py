from __future__ import annotations

from .regions import TERRITORY_REGIONS



def calculate_region_income(region_id: str):
    region = TERRITORY_REGIONS.get(region_id, {})

    return int(region.get("resource_bonus", 0))



def collect_region_income(state: dict, clan_id: str):
    total = 0

    for region_id, region_data in state.get("territories", {}).items():
        if region_data.get("owner") != clan_id:
            continue

        total += calculate_region_income(region_id)

    return total