from __future__ import annotations

import uuid



def create_listing(seller_id: str, item_id: str, price: int):
    return {
        "listing_id": str(uuid.uuid4()),
        "seller_id": seller_id,
        "item_id": item_id,
        "price": int(price),
        "active": True,
    }



def cancel_listing(listing: dict):
    listing["active"] = False
    return listing



def get_active_listings(state: dict):
    return [
        listing
        for listing in state.get("listings", [])
        if listing.get("active")
    ]