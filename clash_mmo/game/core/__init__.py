"""Shared MMO infrastructure systems."""

from .rarity import RARITIES, normalize_rarity, rarity_multiplier
from .profiles import default_player_profile, ensure_player_profile
from .inventory import default_inventory, make_item_stack, make_equipment_item
from .cosmetics import default_cosmetics, unlock_cosmetic, equip_cosmetic
from .matchmaking import default_matchmaking_profile, apply_match_result
from .modifiers import StatBlock, Modifier, calculate_effective_stats
from .events import EventBus, event_bus

__all__ = [
    "RARITIES",
    "normalize_rarity",
    "rarity_multiplier",
    "default_player_profile",
    "ensure_player_profile",
    "default_inventory",
    "make_item_stack",
    "make_equipment_item",
    "default_cosmetics",
    "unlock_cosmetic",
    "equip_cosmetic",
    "default_matchmaking_profile",
    "apply_match_result",
    "StatBlock",
    "Modifier",
    "calculate_effective_stats",
    "EventBus",
    "event_bus",
]