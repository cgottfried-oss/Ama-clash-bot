from __future__ import annotations

import random


BLACK_MARKET_STOCK = {
    # Intentionally expensive: black market is a gold sink and rare-gear shortcut.
    "king_warborn_blade": {"price": 1800, "type": "gear"},
    "queen_warborn_crossbow": {"price": 1800, "type": "gear"},
    "warden_staff_of_embers": {"price": 2200, "type": "gear"},
    "king_guardian_plate": {"price": 3200, "type": "gear"},
    "queen_shadow_cloak": {"price": 3200, "type": "gear"},
}

# Compatibility name used by older imports.
BLACK_MARKET_ITEMS = list(BLACK_MARKET_STOCK.keys())


def rotate_black_market(count: int = 3):
    """Return a rotating purchasable stock list.

    Each entry contains item_id, price, and type so /blackmarket can show prices
    and /blackmarketbuy can validate purchases.
    """
    item_ids = random.sample(
        BLACK_MARKET_ITEMS,
        min(count, len(BLACK_MARKET_ITEMS)),
    )
    return [
        {
            "item_id": item_id,
            **BLACK_MARKET_STOCK[item_id],
        }
        for item_id in item_ids
    ]


def get_black_market_item(item_id: str):
    item_id = str(item_id or "").strip().lower()
    item = BLACK_MARKET_STOCK.get(item_id)
    if not item:
        return None
    return {"item_id": item_id, **item}
