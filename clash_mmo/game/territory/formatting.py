from __future__ import annotations

from .regions import TERRITORY_REGIONS



def format_region_line(region_id: str, owner: str | None):
    region = TERRITORY_REGIONS.get(region_id, {})

    owner_text = owner or "Unclaimed"

    return (
        f"🗺️ **{region.get('name', region_id)}** — "
        f"Owner: {owner_text}"
    )



def format_territory_map(state: dict):
    lines = []

    for region_id in TERRITORY_REGIONS:
        owner = state.get("territories", {}).get(region_id, {}).get("owner")
        lines.append(format_region_line(region_id, owner))

    return "\n".join(lines)