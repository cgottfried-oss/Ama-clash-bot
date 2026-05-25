from __future__ import annotations

from .listings import create_listing
from .pricing import final_sale_amount



def list_inventory_item(state: dict, seller_id: str, item_id: str, price: int):
    state.setdefault("listings", [])

    listing = create_listing(
        seller_id=seller_id,
        item_id=item_id,
        price=price,
    )

    state["listings"].append(listing)

    return listing



def buy_listing(state: dict, listing_id: str, buyer_id: str):
    for listing in state.get("listings", []):
        if listing["listing_id"] != listing_id:
            continue

        if not listing.get("active"):
            return {
                "ok": False,
                "error": "Listing inactive.",
            }

        listing["active"] = False

        return {
            "ok": True,
            "listing": listing,
            "seller_profit": final_sale_amount(listing["price"]),
            "buyer_id": buyer_id,
        }

    return {
        "ok": False,
        "error": "Listing not found.",
    }
