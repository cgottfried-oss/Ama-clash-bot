"""equipment, rarity, and hero systems."""

from .gear_catalog import GEAR_CATALOG, EQUIPMENT_SLOTS
from .heroes import HERO_CATALOG
from .abilities import HERO_ABILITIES
from .loot import roll_equipment_drop
from .service import (
    grant_equipment,
    equip_item,
    get_equipped_items,
    get_effective_profile_stats,
    equip_hero_ability,
)
from .formatting import format_gear_line, format_stats_block, format_hero_line

__all__ = [
    "GEAR_CATALOG",
    "EQUIPMENT_SLOTS",
    "HERO_CATALOG",
    "HERO_ABILITIES",
    "roll_equipment_drop",
    "grant_equipment",
    "equip_item",
    "get_equipped_items",
    "get_effective_profile_stats",
    "equip_hero_ability",
    "format_gear_line",
    "format_stats_block",
    "format_hero_line",
]