from __future__ import annotations



def format_listing(listing: dict):
    return (
        f"Listing ID: {listing['listing_id']}\n"
        f"Item: {listing['item_id']}\n"
        f"Price: {listing['price']:,} Gold"
    )



def format_auction(auction: dict):
    return (
        f"Auction ID: {auction['auction_id']}\n"
        f"Item: {auction['item_id']}\n"
        f"Highest Bid: {auction['highest_bid']:,}"
    )



def format_black_market(items: list[str]):
    return "\n".join([
        f"🕶️ {item_id}"
        for item_id in items
    ])
