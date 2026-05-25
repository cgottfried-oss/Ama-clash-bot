"""Phase 5-6 cooperative real-time PvE systems."""

from .bosses import RAID_BOSSES
from .instances import create_raid_instance, get_active_raid, close_raid
from .phases import get_boss_phase
from .windows import is_damage_window_open, open_damage_window
from .abilities import roll_boss_ability
from .rewards import calculate_raid_rewards
from .service import start_raid, join_raid, attack_raid_boss
from .formatting import format_raid_status, format_attack_result

__all__ = [
    "RAID_BOSSES",
    "create_raid_instance",
    "get_active_raid",
    "close_raid",
    "get_boss_phase",
    "is_damage_window_open",
    "open_damage_window",
    "roll_boss_ability",
    "calculate_raid_rewards",
    "start_raid",
    "join_raid",
    "attack_raid_boss",
    "format_raid_status",
    "format_attack_result",
]
