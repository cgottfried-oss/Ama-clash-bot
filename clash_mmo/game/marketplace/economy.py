from __future__ import annotations

from collections import Counter, defaultdict


RARITY_ORDER = ["common", "rare", "epic", "legendary", "mythic"]


def item_market_traits(item: dict, catalog: dict | None = None) -> dict:
    catalog = catalog or {}
    item_id = str(item.get("item_id") or "unknown")
    gear = catalog.get(item_id, {}) if isinstance(catalog, dict) else {}

    return {
        "item_id": item_id,
        "rarity": str(item.get("rarity") or gear.get("rarity") or "common").lower(),
        "slot": str(item.get("slot") or gear.get("slot") or "unknown").lower(),
        "hero": str(item.get("hero") or gear.get("hero") or "any").lower(),
        "soulbound": bool(item.get("soulbound") or gear.get("soulbound")),
        "untradeable": bool(item.get("untradeable") or gear.get("untradeable")),
        "raid_exclusive": bool(item.get("raid_exclusive") or gear.get("raid_exclusive")),
        "season_exclusive": bool(item.get("season_exclusive") or gear.get("season_exclusive")),
    }


def filter_listings(listings: list[dict], *, rarity: str | None = None, slot: str | None = None, hero: str | None = None, catalog: dict | None = None) -> list[dict]:
    rarity = str(rarity or "").strip().lower()
    slot = str(slot or "").strip().lower()
    hero = str(hero or "").strip().lower()

    filtered = []
    for listing in listings:
        item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
        traits = item_market_traits(item, catalog)

        if rarity and rarity != "any" and traits["rarity"] != rarity:
            continue
        if slot and slot != "any" and traits["slot"] != slot:
            continue
        if hero and hero != "any" and traits["hero"] != hero:
            continue

        filtered.append(listing)

    return filtered


def analyze_marketplace(state: dict, *, catalog: dict | None = None) -> dict:
    market = state.setdefault("marketplace", {})
    listings = [l for l in market.setdefault("listings", []) if l.get("status") == "active" and l.get("active", True)]
    history = market.setdefault("listing_history", [])
    players = state.setdefault("players", {})

    rarity_supply = Counter()
    slot_supply = Counter()
    hero_supply = Counter()
    active_value = 0

    for listing in listings:
        item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
        traits = item_market_traits(item, catalog)
        rarity_supply[traits["rarity"]] += 1
        slot_supply[traits["slot"]] += 1
        hero_supply[traits["hero"]] += 1
        active_value += int(listing.get("price", 0) or 0)

    sale_prices_by_rarity = defaultdict(list)
    for sale in history:
        if sale.get("status") != "sold":
            continue
        item = sale.get("item_snapshot") or sale.get("escrow_item") or {}
        traits = item_market_traits(item, catalog)
        sale_prices_by_rarity[traits["rarity"]].append(int(sale.get("price", 0) or 0))

    average_sale_price_by_rarity = {
        rarity: int(sum(values) / len(values))
        for rarity, values in sale_prices_by_rarity.items()
        if values
    }

    total_player_gold = 0
    for profile in players.values():
        if not isinstance(profile, dict):
            continue
        inventory = profile.get("inventory", {}) if isinstance(profile.get("inventory", {}), dict) else {}
        currencies = inventory.get("currencies", {}) if isinstance(inventory.get("currencies", {}), dict) else {}
        if "gold" in currencies:
            total_player_gold += int(currencies.get("gold", 0) or 0)
        else:
            total_player_gold += int(profile.get("gold", 0) or 0)

    gold_sunk = int(market.get("gold_sunk", 0) or 0)
    sold_count = sum(1 for sale in history if sale.get("status") == "sold")
    listed_count = len(listings)

    inflation_pressure = "low"
    if total_player_gold > 0 and gold_sunk / max(1, total_player_gold) < 0.01 and active_value > total_player_gold * 0.75:
        inflation_pressure = "high"
    elif total_player_gold > 0 and active_value > total_player_gold * 0.35:
        inflation_pressure = "medium"

    scarcity_notes = []
    for rarity in RARITY_ORDER:
        count = rarity_supply.get(rarity, 0)
        if rarity in {"legendary", "mythic"} and count > max(3, listed_count * 0.25):
            scarcity_notes.append(f"{rarity.title()} supply looks high for a rare tier.")
        if rarity in {"epic", "legendary", "mythic"} and sold_count >= 10 and count == 0:
            scarcity_notes.append(f"{rarity.title()} supply is currently scarce.")

    drop_rate_notes = []
    if rarity_supply.get("legendary", 0) + rarity_supply.get("mythic", 0) > rarity_supply.get("common", 0) + rarity_supply.get("rare", 0) and listed_count >= 5:
        drop_rate_notes.append("High-rarity listings outnumber low-rarity listings; consider lowering high-tier drop rates or making more items soulbound.")
    if listed_count == 0 and sold_count == 0:
        drop_rate_notes.append("Not enough market data yet. Keep current drop rates until players create listings and sales.")

    return {
        "active_listings": listed_count,
        "active_value": active_value,
        "sold_count": sold_count,
        "total_player_gold": total_player_gold,
        "gold_sunk": gold_sunk,
        "inflation_pressure": inflation_pressure,
        "rarity_supply": dict(rarity_supply),
        "slot_supply": dict(slot_supply),
        "hero_supply": dict(hero_supply),
        "average_sale_price_by_rarity": average_sale_price_by_rarity,
        "scarcity_notes": scarcity_notes,
        "drop_rate_notes": drop_rate_notes,
    }
