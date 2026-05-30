from __future__ import annotations

import random

from .catalog import event_keys
from .state import get_active_event, start_event

# "Rare/special" tuning: the loop tick interval is set in bot_runner.py.
# At a 2-hour tick with a 25% chance, the average quiet gap between events
# is roughly 6 hours. Adjust ROLL_CHANCE to tune frequency without touching
# the loop itself.
ROLL_CHANCE = 0.25


def maybe_start_event(state: dict, *, chance: float = ROLL_CHANCE, rng=random):
    """If no event is active, roll a chance to start a random one.

    Returns the event key that was started, or None if nothing started
    (either an event was already active, or the roll failed).
    """
    if get_active_event(state) is not None:
        return None

    if rng.random() >= float(chance):
        return None

    key = rng.choice(event_keys())
    start_event(state, key)
    return key
