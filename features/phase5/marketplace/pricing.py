from __future__ import annotations

from .config import MARKETPLACE_CONFIG



def calculate_tax(amount: int, auction: bool = False):
    rate = MARKETPLACE_CONFIG["auction_tax"] if auction else MARKETPLACE_CONFIG["listing_tax"]

    return int(amount * rate)



def final_sale_amount(amount: int, auction: bool = False):
    return int(amount) - calculate_tax(amount, auction=auction)
