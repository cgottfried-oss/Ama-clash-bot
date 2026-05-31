"""clan territory map systems."""

from .regions import TERRITORY_REGIONS
from .ownership import claim_region, get_region_owner, release_region
from .resources import calculate_region_income, collect_region_income
from .conquest import resolve_conquest
from .npc_raids import run_npc_territory_raids
from .season import current_territory_season, add_conquest_points
from .formatting import format_region_line, format_territory_map

__all__ = [
    "TERRITORY_REGIONS",
    "claim_region",
    "get_region_owner",
    "release_region",
    "calculate_region_income",
    "collect_region_income",
    "resolve_conquest",
    "run_npc_territory_raids",
    "current_territory_season",
    "add_conquest_points",
    "format_region_line",
    "format_territory_map",
]