from __future__ import annotations

import uuid



def create_auction(seller_id: str, item_id: str, starting_bid: int):
    return {
        "auction_id": str(uuid.uuid4()),
        "seller_id": seller_id,
        "item_id": item_id,
        "highest_bid": int(starting_bid),
        "highest_bidder": None,
        "active": True,
    }



def place_bid(auction: dict, bidder_id: str, amount: int):
    if amount <= auction["highest_bid"]:
        return False

    auction["highest_bid"] = int(amount)
    auction["highest_bidder"] = bidder_id

    return True



def close_auction(auction: dict):
    auction["active"] = False
    return auction
