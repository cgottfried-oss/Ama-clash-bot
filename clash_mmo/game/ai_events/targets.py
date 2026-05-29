from __future__ import annotations

import random


EVENT_TARGETS = [
    "territories",
    "marketplace",
    "raids",
    "matchmaking",
    "seasonal_ladder",
]



def pick_event_target():
    return random.choice(EVENT_TARGETS)
