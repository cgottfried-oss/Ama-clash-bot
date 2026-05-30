from __future__ import annotations

from .catalog import get_event_config
from .state import get_active_event_key


def get_active_effect(state: dict, effect_key: str, default):
    """Return the value of `effect_key` from the currently active event,
    or `default` if no event is active or the event lacks that effect.

    This is the single read path consumers use so event effects stay
    consistent and auditable. Example:
        mult = get_active_effect(state, "war_reward_multiplier", 1.0)
    """
    key = get_active_event_key(state)
    if not key:
        return default

    config = get_event_config(key)
    if not config:
        return default

    effects = config.get("effects", {}) or {}
    if effect_key not in effects:
        return default

    return effects[effect_key]
