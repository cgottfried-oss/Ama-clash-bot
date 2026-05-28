from __future__ import annotations

import copy
import uuid

from clash_mmo.game.core.inventory import ensure_item_instance_id

from .config import MARKETPLACE_CONFIG
from .pricing import calculate_tax, final_sale_amount


MIN_LISTING_PRICE = 1


def _players(state: dict) -> dict:
    return state.setdefault("players", {})


def _profile(state: dict, user_id: str) -> dict | None:
    return _players(state).get(str(user_id))


def _inventory(profile: dict) -> dict:
    return profile.setdefault("inventory", {"currencies": {}, "items": [], "equipment": {}})


def _currency_bucket(profile: dict) -> dict:
    inventory = _inventory(profile)
    return inventory.setdefault("currencies", {})


def _get_gold(profile: dict) -> int:
    currencies = _currency_bucket(profile)
    if "gold" in currencies:
        return int(currencies.get("gold", 0) or 0)
    return int(profile.get("gold", 0) or 0)


def _set_gold(profile: dict, amount: int) -> None:
    amount = max(0, int(amount or 0))
    _currency_bucket(profile)["gold"] = amount
    if "gold" in profile:
        profile["gold"] = amount


def _active_listings(state: dict) -> list[dict]:
    market = state.setdefault("marketplace", {})
    return market.setdefault("listings", [])


def _find_item(profile: dict, item_instance_id: str) -> tuple[int, dict] | tuple[None, None]:
    items = _inventory(profile).setdefault("items", [])
    target = str(item_instance_id or "").strip()

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue

        instance_id = ensure_item_instance_id(item)
        if instance_id == target:
            return index, item

    return None, None


def _is_equipped(profile: dict, item_instance_id: str) -> bool:
    target = str(item_instance_id or "").strip()
    heroes = profile.get("heroes", {})

    if isinstance(heroes, dict):
        for hero in heroes.values():
            if not isinstance(hero, dict):
                continue
            equipment = hero.get("equipment", {})
            if not isinstance(equipment, dict):
                continue
            for equipped in equipment.values():
                if isinstance(equipped, dict) and str(equipped.get("instance_id") or "") == target:
                    return True

    inventory_equipment = _inventory(profile).get("equipment", {})
    if isinstance(inventory_equipment, dict):
        for equipped in inventory_equipment.values():
            if isinstance(equipped, dict) and str(equipped.get("instance_id") or "") == target:
                return True

    return False


def _find_listing(state: dict, listing_id: str) -> dict | None:
    target = str(listing_id or "").strip()
    for listing in _active_listings(state):
        if str(listing.get("listing_id") or "") == target:
            return listing
    return None


def get_active_listings(state: dict) -> list[dict]:
    return [
        listing
        for listing in _active_listings(state)
        if listing.get("status") == "active" and listing.get("active", True)
    ]


def create_market_listing(state: dict, seller_id: str, item_instance_id: str, price: int, *, now: int | None = None) -> dict:
    seller_id = str(seller_id)
    item_instance_id = str(item_instance_id or "").strip()
    price = int(price or 0)

    if price < MIN_LISTING_PRICE:
        return {"ok": False, "error": f"Listing price must be at least {MIN_LISTING_PRICE} gold."}

    seller = _profile(state, seller_id)
    if not seller:
        return {"ok": False, "error": "Seller profile not found."}

    seller_active_count = sum(1 for listing in get_active_listings(state) if str(listing.get("seller_id")) == seller_id)
    max_active = int(MARKETPLACE_CONFIG.get("max_active_listings", 10) or 10)
    if seller_active_count >= max_active:
        return {"ok": False, "error": f"You already have {max_active} active listings."}

    if _is_equipped(seller, item_instance_id):
        return {"ok": False, "error": "Unequip this item before listing it."}

    item_index, item = _find_item(seller, item_instance_id)
    if item_index is None or item is None:
        return {"ok": False, "error": "Item not found in seller inventory."}

    if item.get("locked") or item.get("soulbound") or item.get("bound"):
        return {"ok": False, "error": "This item cannot be listed."}

    item_snapshot = copy.deepcopy(item)
    inventory_items = _inventory(seller).setdefault("items", [])
    escrow_item = inventory_items.pop(item_index)

    listing = {
        "listing_id": str(uuid.uuid4()),
        "seller_id": seller_id,
        "item_instance_id": ensure_item_instance_id(escrow_item),
        "item_id": escrow_item.get("item_id"),
        "item_snapshot": item_snapshot,
        "escrow_item": escrow_item,
        "price": price,
        "tax": calculate_tax(price),
        "seller_receives": final_sale_amount(price),
        "status": "active",
        "active": True,
        "created_at": int(now or 0),
        "buyer_id": None,
        "closed_at": None,
    }

    _active_listings(state).append(listing)
    return {"ok": True, "listing": listing}


def buy_market_listing(state: dict, buyer_id: str, listing_id: str, *, now: int | None = None) -> dict:
    buyer_id = str(buyer_id)
    listing = _find_listing(state, listing_id)

    if not listing:
        return {"ok": False, "error": "Listing not found."}

    if listing.get("status") != "active" or not listing.get("active", True):
        return {"ok": False, "error": "Listing is not active."}

    seller_id = str(listing.get("seller_id"))
    if buyer_id == seller_id:
        return {"ok": False, "error": "You cannot buy your own listing."}

    buyer = _profile(state, buyer_id)
    seller = _profile(state, seller_id)

    if not buyer:
        return {"ok": False, "error": "Buyer profile not found."}
    if not seller:
        return {"ok": False, "error": "Seller profile not found."}

    price = int(listing.get("price", 0) or 0)
    if _get_gold(buyer) < price:
        return {"ok": False, "error": "Buyer does not have enough gold."}

    escrow_item = listing.get("escrow_item") or listing.get("item_snapshot")
    if not isinstance(escrow_item, dict):
        return {"ok": False, "error": "Listing escrow item missing."}

    seller_receives = final_sale_amount(price)
    tax = calculate_tax(price)

    _set_gold(buyer, _get_gold(buyer) - price)
    _set_gold(seller, _get_gold(seller) + seller_receives)

    _inventory(buyer).setdefault("items", []).append(copy.deepcopy(escrow_item))

    listing["status"] = "sold"
    listing["active"] = False
    listing["buyer_id"] = buyer_id
    listing["closed_at"] = int(now or 0)
    listing["tax"] = tax
    listing["seller_receives"] = seller_receives

    return {
        "ok": True,
        "listing": listing,
        "item": escrow_item,
        "price": price,
        "tax": tax,
        "seller_receives": seller_receives,
    }


def cancel_market_listing(state: dict, seller_id: str, listing_id: str, *, now: int | None = None) -> dict:
    seller_id = str(seller_id)
    listing = _find_listing(state, listing_id)

    if not listing:
        return {"ok": False, "error": "Listing not found."}

    if str(listing.get("seller_id")) != seller_id:
        return {"ok": False, "error": "Only the seller can cancel this listing."}

    if listing.get("status") != "active" or not listing.get("active", True):
        return {"ok": False, "error": "Listing is not active."}

    seller = _profile(state, seller_id)
    if not seller:
        return {"ok": False, "error": "Seller profile not found."}

    escrow_item = listing.get("escrow_item") or listing.get("item_snapshot")
    if not isinstance(escrow_item, dict):
        return {"ok": False, "error": "Listing escrow item missing."}

    _inventory(seller).setdefault("items", []).append(copy.deepcopy(escrow_item))

    listing["status"] = "cancelled"
    listing["active"] = False
    listing["closed_at"] = int(now or 0)

    return {"ok": True, "listing": listing, "item": escrow_item}


# Backwards-compatible aliases for old imports.
def list_inventory_item(state: dict, seller_id: str, item_id: str, price: int):
    return create_market_listing(state, seller_id, item_id, price)


def buy_listing(state: dict, listing_id: str, buyer_id: str):
    return buy_market_listing(state, buyer_id, listing_id)
