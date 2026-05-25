from __future__ import annotations

import random


BLACK_MARKET_ITEMS = [
    "legend_plate",
    "warborn_helm",
    "legend_flames",
    "warden_staff",
]



def rotate_black_market(count: int = 3):
    return random.sample(
        BLACK_MARKET_ITEMS,
        min(count, len(BLACK_MARKET_ITEMS)),
    )
