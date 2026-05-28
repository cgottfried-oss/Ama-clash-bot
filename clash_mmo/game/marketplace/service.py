from __future__ import annotations

import copy
import uuid

from clash_mmo.game.core.inventory import ensure_item_instance_id

from .config import MARKETPLACE_CONFIG
from .pricing import calculate_tax, final_sale_amount


MIN_LISTING_PRICE = 1


# ---------- internal helpers ----------

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



def _market(state: dict) -> dict:
    market = state.setdefault("marketplace", {})
    market.setdefault("listings", [])
    market.setdefault("listing_history", [])
    market.setdefault("trades", [])
    market.setdefault("trade_logs", [])
    market.setdefault("stats", {})
    market.setdefault("gold_sunk", 0)
    return market



def _active_listings(state: dict) -> list[dict]:
    return _market(state).setdefault("listings", [])



def _trade_log(state: dict) -> list[dict]:
    return _market(state).setdefault("trade_logs", [])



def _listing_history(state: dict) -> list[dict]:
    return _market(state).setdefault("listing_history", [])



def _active_trades(state: dict) -> list[dict]:
    return _market(state).setdefault("trades", [])



def _market_stats(state: dict) -> dict:
    return _market(state).setdefault("stats", {})



def _append_history(history: list[dict], entry: dict, limit: int):
    history.append(entry)
    while len(history) > limit:
        history.pop(0)



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



def _find_trade(state: dict, trade_id: str) -> dict | None:
    target = str(trade_id or "").strip()
    for trade in _active_trades(state):
        if str(trade.get("trade_id") or "") == target:
            return trade
    return None



def _increment_stat(state: dict, user_id: str, key: str, amount: int = 1):
    stats = _market_stats(state)
    user_stats = stats.setdefault(str(user_id), {})
    user_stats[key] = int(user_stats.get(key, 0) or 0) + int(amount or 0)



def expire_marketplace_entries(state: dict, *, now: int):
    now = int(now or 0)

    listing_duration = int(MARKETPLACE_CONFIG.get("listing_duration_seconds", 0) or 0)
    trade_duration = int(MARKETPLACE_CONFIG.get("trade_duration_seconds", 0) or 0)

    for listing in _active_listings(state):
        if listing.get("status") != "active":
            continue

        created_at = int(listing.get("created_at", 0) or 0)
        if listing_duration <= 0 or created_at <= 0:
            continue

        if now - created_at < listing_duration:
            continue

        seller = _profile(state, listing.get("seller_id"))
        escrow_item = listing.get("escrow_item")

        if seller and isinstance(escrow_item, dict):
            _inventory(seller).setdefault("items", []).append(copy.deepcopy(escrow_item))

        listing["status"] = "expired"
        listing["active"] = False
        listing["closed_at"] = now

    for trade in _active_trades(state):
        if trade.get("status") != "pending":
            continue

        created_at = int(trade.get("created_at", 0) or 0)
        if trade_duration <= 0 or created_at <= 0:
            continue

        if now - created_at < trade_duration:
            continue

        sender = _profile(state, trade.get("sender_id"))
        escrow_item = trade.get("sender_item")

        if sender and isinstance(escrow_item, dict):
            _inventory(sender).setdefault("items", []).append(copy.deepcopy(escrow_item))

        trade["status"] = "expired"
        trade["closed_at"] = now


# ---------- marketplace listings ----------

def get_active_listings(state: dict) -> list[dict]:
    return [listing for listing in _active_listings(state) if listing.get("status") == "active" and listing.get("active", True)]



def create_market_listing(state: dict, seller_id: str, item_instance_id: str, price: int, *, now: int | None = None) -> dict:
    seller_id = str(seller_id)
    item_instance_id = str(item_instance_id or "").strip()
    price = int(price or 0)
    now = int(now or 0)

    expire_marketplace_entries(state, now=now)

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
        "created_at": now,
        "expires_at": now + int(MARKETPLACE_CONFIG.get("listing_duration_seconds", 0) or 0),
        "buyer_id": None,
        "closed_at": None,
    }

    _active_listings(state).append(listing)

    _increment_stat(state, seller_id, "items_listed", 1)

    return {"ok": True, "listing": listing}



def buy_market_listing(state: dict, buyer_id: str, listing_id: str, *, now: int | None = None) -> dict:
    buyer_id = str(buyer_id)
    now = int(now or 0)

    expire_marketplace_entries(state, now=now)

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

    _market(state)["gold_sunk"] = int(_market(state).get("gold_sunk", 0) or 0) + tax

    _inventory(buyer).setdefault("items", []).append(copy.deepcopy(escrow_item))

    listing["status"] = "sold"
    listing["active"] = False
    listing["buyer_id"] = buyer_id
    listing["closed_at"] = now
    listing["tax"] = tax
    listing["seller_receives"] = seller_receives

    _append_history(_listing_history(state), copy.deepcopy(listing), int(MARKETPLACE_CONFIG.get("history_limit", 100) or 100))

    _increment_stat(state, seller_id, "items_sold", 1)
    _increment_stat(state, seller_id, "gold_earned", seller_receives)
    _increment_stat(state, buyer_id, "items_bought", 1)
    _increment_stat(state, buyer_id, "gold_spent", price)

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
    now = int(now or 0)

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
    listing["closed_at"] = now

    return {"ok": True, "listing": listing, "item": escrow_item}


# ---------- player trades ----------

def create_trade_offer(state: dict, sender_id: str, target_id: str, item_instance_id: str, requested_gold: int = 0, *, now: int | None = None) -> dict:
    sender_id = str(sender_id)
    target_id = str(target_id)
    item_instance_id = str(item_instance_id or "").strip()
    requested_gold = max(0, int(requested_gold or 0))
    now = int(now or 0)

    expire_marketplace_entries(state, now=now)

    if sender_id == target_id:
        return {"ok": False, "error": "You cannot trade with yourself."}

    sender = _profile(state, sender_id)
    target = _profile(state, target_id)

    if not sender:
        return {"ok": False, "error": "Sender profile not found."}
    if not target:
        return {"ok": False, "error": "Target profile not found."}

    if _is_equipped(sender, item_instance_id):
        return {"ok": False, "error": "Unequip this item before trading it."}

    item_index, item = _find_item(sender, item_instance_id)
    if item_index is None or item is None:
        return {"ok": False, "error": "Item not found in inventory."}

    inventory_items = _inventory(sender).setdefault("items", [])
    escrow_item = inventory_items.pop(item_index)

    trade = {
        "trade_id": str(uuid.uuid4()),
        "sender_id": sender_id,
        "target_id": target_id,
        "sender_item": escrow_item,
        "requested_gold": requested_gold,
        "status": "pending",
        "created_at": now,
        "expires_at": now + int(MARKETPLACE_CONFIG.get("trade_duration_seconds", 0) or 0),
        "closed_at": None,
    }

    _active_trades(state).append(trade)

    _increment_stat(state, sender_id, "trades_created", 1)

    return {"ok": True, "trade": trade}



def accept_trade_offer(state: dict, target_id: str, trade_id: str, *, now: int | None = None) -> dict:
    target_id = str(target_id)
    now = int(now or 0)

    expire_marketplace_entries(state, now=now)

    trade = _find_trade(state, trade_id)

    if not trade:
        return {"ok": False, "error": "Trade not found."}

    if trade.get("status") != "pending":
        return {"ok": False, "error": "Trade is no longer pending."}

    if str(trade.get("target_id")) != target_id:
        return {"ok": False, "error": "This trade was not sent to you."}

    sender = _profile(state, trade.get("sender_id"))
    target = _profile(state, target_id)

    if not sender or not target:
        return {"ok": False, "error": "Trade participant missing."}

    requested_gold = int(trade.get("requested_gold", 0) or 0)

    if _get_gold(target) < requested_gold:
        return {"ok": False, "error": "You do not have enough gold for this trade."}

    tax = int(requested_gold * float(MARKETPLACE_CONFIG.get("trade_gold_tax", 0.02) or 0.02))
    payout = requested_gold - tax

    _set_gold(target, _get_gold(target) - requested_gold)
    _set_gold(sender, _get_gold(sender) + payout)

    _market(state)["gold_sunk"] = int(_market(state).get("gold_sunk", 0) or 0) + tax

    item = trade.get("sender_item")
    if isinstance(item, dict):
        _inventory(target).setdefault("items", []).append(copy.deepcopy(item))

    trade["status"] = "accepted"
    trade["closed_at"] = now
    trade["trade_tax"] = tax

    _append_history(_trade_log(state), copy.deepcopy(trade), int(MARKETPLACE_CONFIG.get("trade_log_limit", 100) or 100))

    _increment_stat(state, trade.get("sender_id"), "trades_completed", 1)
    _increment_stat(state, target_id, "trades_completed", 1)

    return {
        "ok": True,
        "trade": trade,
        "item": item,
        "trade_tax": tax,
    }



def decline_trade_offer(state: dict, target_id: str, trade_id: str, *, now: int | None = None) -> dict:
    target_id = str(target_id)
    now = int(now or 0)

    trade = _find_trade(state, trade_id)

    if not trade:
        return {"ok": False, "error": "Trade not found."}

    if str(trade.get("target_id")) != target_id:
        return {"ok": False, "error": "This trade was not sent to you."}

    if trade.get("status") != "pending":
        return {"ok": False, "error": "Trade is no longer pending."}

    sender = _profile(state, trade.get("sender_id"))
    escrow_item = trade.get("sender_item")

    if sender and isinstance(escrow_item, dict):
        _inventory(sender).setdefault("items", []).append(copy.deepcopy(escrow_item))

    trade["status"] = "declined"
    trade["closed_at"] = now

    return {"ok": True, "trade": trade}
