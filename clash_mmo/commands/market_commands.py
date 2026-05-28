from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.core.inventory import ensure_item_instance_id
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.crafting import (
    get_next_upgrade_cost,
    get_salvage_rewards,
    get_upgrade_level,
    salvage_item,
    upgrade_item,
)
from clash_mmo.game.marketplace import (
    cancel_market_listing,
    buy_market_listing,
    format_black_market,
    get_active_listings,
    rotate_black_market,
)
from clash_mmo.game.marketplace.economy import analyze_marketplace, filter_listings
from clash_mmo.game.marketplace.service import (
    accept_trade_offer,
    create_market_listing,
    create_trade_offer,
    decline_trade_offer,
    expire_marketplace_entries,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state

RARITY_CHOICES = [
    app_commands.Choice(name="Any", value="any"),
    app_commands.Choice(name="Common", value="common"),
    app_commands.Choice(name="Rare", value="rare"),
    app_commands.Choice(name="Epic", value="epic"),
    app_commands.Choice(name="Legendary", value="legendary"),
]

SLOT_CHOICES = [
    app_commands.Choice(name="Any", value="any"),
    app_commands.Choice(name="Weapon", value="weapon"),
    app_commands.Choice(name="Armor", value="armor"),
    app_commands.Choice(name="Relic", value="relic"),
]

HERO_CHOICES = [
    app_commands.Choice(name="Any", value="any"),
    app_commands.Choice(name="Barbarian King", value="king"),
    app_commands.Choice(name="Archer Queen", value="queen"),
    app_commands.Choice(name="Grand Warden", value="warden"),
]

CURRENCY_NAMES = {
    "gold": "Gold",
    "elixir": "Elixir",
    "dark_elixir": "Dark Elixir",
    "gems": "Gems",
    "raid_medals": "Raid Medals",
    "shiny_ore": "Shiny Ore",
    "glowy_ore": "Glowy Ore",
    "starry_ore": "Starry Ore",
}


def _players(state: dict) -> dict:
    return state.setdefault("players", {})


def _profile(state: dict, user_id: str) -> dict:
    return _players(state).get(str(user_id), {})


def _inventory_items_for_user(state: dict, user_id: str) -> list[dict]:
    profile = _profile(state, user_id)
    inventory = profile.get("inventory", {}) if isinstance(profile, dict) else {}
    items = inventory.get("items", []) if isinstance(inventory, dict) else []
    out = []
    for item in items:
        if isinstance(item, dict):
            ensure_item_instance_id(item)
            out.append(item)
    return out


def _item_name(item: dict) -> str:
    item_id = str(item.get("item_id") or "unknown")
    gear = GEAR_CATALOG.get(item_id, {})
    base_name = str(gear.get("name") or item_id.replace("_", " ").title())
    plus = int(item.get("upgrade_level", item.get("plus", 0)) or 0)
    return f"{base_name} +{plus}" if plus > 0 else base_name


def _short_id(value: str) -> str:
    value = str(value or "")
    return value.split("-")[0] if value else "unknown"


def _format_rewards(rewards: dict) -> str:
    if not rewards:
        return "No rewards"
    return ", ".join(
        f"**{int(amount):,} {CURRENCY_NAMES.get(currency, currency.replace('_', ' ').title())}**"
        for currency, amount in rewards.items()
        if int(amount or 0) > 0
    ) or "No rewards"


def _format_listing_line(listing: dict) -> str:
    item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
    item_id = str(listing.get("item_id") or item.get("item_id") or "unknown")
    gear = GEAR_CATALOG.get(item_id, {})
    name = _item_name(item)
    rarity = str(item.get("rarity") or gear.get("rarity") or "common").title()
    slot = str(item.get("slot") or gear.get("slot") or "unknown").title()
    hero = str(item.get("hero") or gear.get("hero") or "any").replace("_", " ").title()
    level = int(item.get("level", 1) or 1)
    price = int(listing.get("price", 0) or 0)
    seller_receives = int(listing.get("seller_receives", 0) or 0)
    listing_id = str(listing.get("listing_id") or "")
    expires_at = int(listing.get("expires_at", 0) or 0)
    expires_text = f" • Expires <t:{expires_at}:R>" if expires_at else ""
    return (
        f"`{_short_id(listing_id)}` **{name}** [{rarity}] Lv.{level}\n"
        f"Slot: **{slot}** • Hero: **{hero}**\n"
        f"Price: **{price:,} Gold** • Seller receives: **{seller_receives:,}**{expires_text}"
    )


def _format_trade_line(trade: dict, *, viewer_id: str | None = None) -> str:
    item = trade.get("sender_item") or {}
    trade_id = str(trade.get("trade_id") or "")
    sender_id = str(trade.get("sender_id") or "")
    target_id = str(trade.get("target_id") or "")
    requested_gold = int(trade.get("requested_gold", 0) or 0)
    expires_at = int(trade.get("expires_at", 0) or 0)
    direction = "Incoming" if viewer_id and str(viewer_id) == target_id else "Outgoing"
    expires_text = f" • Expires <t:{expires_at}:R>" if expires_at else ""
    return (
        f"`{_short_id(trade_id)}` **{direction} Trade**\n"
        f"Item: **{_item_name(item)}** • Requested Gold: **{requested_gold:,}**\n"
        f"From: <@{sender_id}> • To: <@{target_id}>{expires_text}"
    )


def _format_counter(counter: dict, *, empty: str = "No data") -> str:
    if not counter:
        return empty
    parts = [f"{str(key).title()}: **{int(value):,}**" for key, value in sorted(counter.items())]
    return "\n".join(parts[:10]) or empty


def register_market_commands(bot, ctx):
    async def item_instance_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        state = await load_mmo_state(ctx)
        items = _inventory_items_for_user(state, str(interaction.user.id))
        current = str(current or "").lower().strip()
        choices = []
        for item in items:
            instance_id = ensure_item_instance_id(item)
            name = _item_name(item)
            rarity = str(item.get("rarity", "common")).title()
            level = int(item.get("level", 1) or 1)
            haystack = f"{name} {item.get('item_id')} {instance_id}".lower()
            if current and current not in haystack:
                continue
            choices.append(app_commands.Choice(name=f"{name} [{rarity}] Lv.{level} • {_short_id(instance_id)}"[:100], value=instance_id[:100]))
            if len(choices) >= 25:
                break
        return choices

    async def listing_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        state = await load_mmo_state(ctx)
        listings = get_active_listings(state)
        current = str(current or "").lower().strip()
        choices = []
        for listing in listings:
            listing_id = str(listing.get("listing_id") or "")
            item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
            item_name = _item_name(item)
            seller_id = str(listing.get("seller_id") or "")
            price = int(listing.get("price", 0) or 0)
            haystack = f"{listing_id} {item_name} {seller_id}".lower()
            if current and current not in haystack:
                continue
            choices.append(app_commands.Choice(name=f"{_short_id(listing_id)} • {item_name} • {price:,} Gold"[:100], value=listing_id[:100]))
            if len(choices) >= 25:
                break
        return choices

    async def trade_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        state = await load_mmo_state(ctx)
        market = state.setdefault("marketplace", {})
        trades = market.setdefault("trades", [])
        viewer_id = str(interaction.user.id)
        current = str(current or "").lower().strip()
        choices = []
        for trade in trades:
            if trade.get("status") != "pending":
                continue
            if viewer_id not in {str(trade.get("sender_id")), str(trade.get("target_id"))}:
                continue
            trade_id = str(trade.get("trade_id") or "")
            item = trade.get("sender_item") or {}
            item_name = _item_name(item)
            haystack = f"{trade_id} {item_name} {trade.get('sender_id')} {trade.get('target_id')}".lower()
            if current and current not in haystack:
                continue
            label = f"{_short_id(trade_id)} • {item_name} • {int(trade.get('requested_gold', 0) or 0):,} Gold"
            choices.append(app_commands.Choice(name=label[:100], value=trade_id[:100]))
            if len(choices) >= 25:
                break
        return choices

    @bot.tree.command(name="upgradegear", description="Upgrade gear up to +12 using Clash resources")
    @app_commands.describe(item="Choose a gear item to upgrade")
    @app_commands.autocomplete(item=item_instance_autocomplete)
    async def upgradegear(interaction: discord.Interaction, item: str):
        state = await load_mmo_state(ctx)
        preview_item = None
        for owned_item in _inventory_items_for_user(state, str(interaction.user.id)):
            if ensure_item_instance_id(owned_item) == item:
                preview_item = owned_item
                break

        if preview_item:
            rarity = str(preview_item.get("rarity") or "common").lower()
            current_plus = get_upgrade_level(preview_item)
            preview_cost = get_next_upgrade_cost(rarity, current_plus)
        else:
            current_plus = 0
            preview_cost = {}

        result_box = {}

        def _update(state_data):
            result_box.update(upgrade_item(state_data, str(interaction.user.id), item))
            return state_data

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            cost_text = f"\nNext cost would be: {_format_rewards(preview_cost)}" if preview_cost else ""
            await interaction.response.send_message(
                f"❌ {result_box.get('error', 'Could not upgrade item.')}{cost_text}",
                ephemeral=True,
            )
            return

        upgraded_item = result_box.get("item", {})
        cost = result_box.get("cost", {})
        new_plus = int(result_box.get("upgrade_level", current_plus + 1) or 0)
        stat_multiplier = float(upgraded_item.get("stat_multiplier", 1.0) or 1.0)

        await interaction.response.send_message(
            f"⬆️ Upgraded **{_item_name(upgraded_item)}** to **+{new_plus}**.\n"
            f"Cost: {_format_rewards(cost)}\n"
            f"Stat Multiplier: **{stat_multiplier:.2f}x**"
        )

    @bot.tree.command(name="salvage", description="Salvage unwanted gear into Clash resources")
    @app_commands.describe(item="Choose a gear item to permanently destroy")
    @app_commands.autocomplete(item=item_instance_autocomplete)
    async def salvage(interaction: discord.Interaction, item: str):
        state = await load_mmo_state(ctx)
        preview_item = None
        for owned_item in _inventory_items_for_user(state, str(interaction.user.id)):
            if ensure_item_instance_id(owned_item) == item:
                preview_item = owned_item
                break

        preview_rewards = get_salvage_rewards(str((preview_item or {}).get("rarity") or "common"))
        result_box = {}

        def _update(state_data):
            result_box.update(salvage_item(state_data, str(interaction.user.id), item))
            return state_data

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not salvage item.')}", ephemeral=True)
            return

        salvaged_item = result_box.get("item", {})
        rewards = result_box.get("rewards") or preview_rewards
        await interaction.response.send_message(
            f"♻️ Salvaged **{_item_name(salvaged_item)}**.\n"
            f"Received: {_format_rewards(rewards)}"
        )

    @bot.tree.command(name="marketsell", description="List one of your gear items on the player marketplace")
    @app_commands.describe(item="Choose an item from your inventory", price="Listing price in Gold")
    @app_commands.autocomplete(item=item_instance_autocomplete)
    async def marketsell(interaction: discord.Interaction, item: str, price: int):
        result_box = {}
        def _update(state):
            result_box.update(create_market_listing(state, str(interaction.user.id), item, price, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not list item.')}", ephemeral=True)
            return
        listing = result_box["listing"]
        listed_item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
        await interaction.response.send_message(f"📦 Listed **{_item_name(listed_item)}** for **{int(price):,} Gold**.\nListing ID: `{_short_id(listing['listing_id'])}`")

    @bot.tree.command(name="market", description="Browse active player marketplace listings")
    @app_commands.describe(rarity="Filter by rarity", slot="Filter by gear slot", hero="Filter by hero")
    @app_commands.choices(rarity=RARITY_CHOICES, slot=SLOT_CHOICES, hero=HERO_CHOICES)
    async def market(interaction: discord.Interaction, rarity: str = "any", slot: str = "any", hero: str = "any"):
        def _update(state_data):
            expire_marketplace_entries(state_data, now=int(ctx.now()))
            return state_data
        await update_mmo_state(ctx, _update)
        state = await load_mmo_state(ctx)
        listings = filter_listings(get_active_listings(state), rarity=rarity, slot=slot, hero=hero, catalog=GEAR_CATALOG)
        if not listings:
            await interaction.response.send_message("Marketplace has no matching listings.", ephemeral=True)
            return
        filter_text = f"Rarity: {rarity.title()} • Slot: {slot.title()} • Hero: {hero.title()}"
        embed = discord.Embed(title="Player Marketplace", description="\n\n".join(_format_listing_line(listing) for listing in listings[:10]), color=0x2ECC71)
        embed.set_footer(text=f"{filter_text} • Showing {min(len(listings), 10)}/{len(listings)} listings")
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="marketbuy", description="Buy a player marketplace listing")
    @app_commands.describe(listing="Marketplace listing ID")
    @app_commands.autocomplete(listing=listing_autocomplete)
    async def marketbuy(interaction: discord.Interaction, listing: str):
        result_box = {}
        def _update(state):
            result_box.update(buy_market_listing(state, str(interaction.user.id), listing, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not buy listing.')}", ephemeral=True)
            return
        bought_item = result_box.get("item", {})
        price = int(result_box.get("price", 0) or 0)
        await interaction.response.send_message(f"🛒 Purchased **{_item_name(bought_item)}** for **{price:,} Gold**.")

    @bot.tree.command(name="marketcancel", description="Cancel one of your active marketplace listings")
    @app_commands.describe(listing="Marketplace listing ID")
    @app_commands.autocomplete(listing=listing_autocomplete)
    async def marketcancel(interaction: discord.Interaction, listing: str):
        result_box = {}
        def _update(state):
            result_box.update(cancel_market_listing(state, str(interaction.user.id), listing, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not cancel listing.')}", ephemeral=True)
            return
        returned_item = result_box.get("item", {})
        await interaction.response.send_message(f"↩️ Cancelled listing and returned **{_item_name(returned_item)}** to your inventory.")

    @bot.tree.command(name="tradeoffer", description="Offer one of your gear items to another player for Gold")
    @app_commands.describe(user="Player receiving the trade", item="Item you are offering", requested_gold="Gold requested from the other player")
    @app_commands.autocomplete(item=item_instance_autocomplete)
    async def tradeoffer(interaction: discord.Interaction, user: discord.Member, item: str, requested_gold: int = 0):
        result_box = {}
        def _update(state):
            result_box.update(create_trade_offer(state, str(interaction.user.id), str(user.id), item, requested_gold, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not create trade.')}", ephemeral=True)
            return
        trade = result_box["trade"]
        item_data = trade.get("sender_item") or {}
        await interaction.response.send_message(f"🤝 Trade offered to {user.mention}: **{_item_name(item_data)}** for **{int(requested_gold or 0):,} Gold**.\nTrade ID: `{_short_id(trade['trade_id'])}`")

    @bot.tree.command(name="trades", description="View your pending player trades")
    async def trades(interaction: discord.Interaction):
        def _update(state_data):
            expire_marketplace_entries(state_data, now=int(ctx.now()))
            return state_data
        await update_mmo_state(ctx, _update)
        state = await load_mmo_state(ctx)
        market_data = state.setdefault("marketplace", {})
        viewer_id = str(interaction.user.id)
        pending = [trade for trade in market_data.setdefault("trades", []) if trade.get("status") == "pending" and viewer_id in {str(trade.get("sender_id")), str(trade.get("target_id"))}]
        if not pending:
            await interaction.response.send_message("You have no pending trades.", ephemeral=True)
            return
        embed = discord.Embed(title="Pending Trades", description="\n\n".join(_format_trade_line(trade, viewer_id=viewer_id) for trade in pending[:10]), color=0x3498DB)
        embed.set_footer(text="Use /tradeaccept or /tradedecline with the trade ID.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="tradeaccept", description="Accept a pending trade sent to you")
    @app_commands.describe(trade="Trade ID")
    @app_commands.autocomplete(trade=trade_autocomplete)
    async def tradeaccept(interaction: discord.Interaction, trade: str):
        result_box = {}
        def _update(state):
            result_box.update(accept_trade_offer(state, str(interaction.user.id), trade, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not accept trade.')}", ephemeral=True)
            return
        item_data = result_box.get("item", {})
        await interaction.response.send_message(f"✅ Accepted trade and received **{_item_name(item_data)}**.")

    @bot.tree.command(name="tradedecline", description="Decline a pending trade sent to you")
    @app_commands.describe(trade="Trade ID")
    @app_commands.autocomplete(trade=trade_autocomplete)
    async def tradedecline(interaction: discord.Interaction, trade: str):
        result_box = {}
        def _update(state):
            result_box.update(decline_trade_offer(state, str(interaction.user.id), trade, now=int(ctx.now())))
            return state
        await update_mmo_state(ctx, _update)
        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not decline trade.')}", ephemeral=True)
            return
        await interaction.response.send_message("❌ Trade declined. The item was returned to the sender.", ephemeral=True)

    @bot.tree.command(name="marketstats", description="View marketplace economy stats")
    async def marketstats(interaction: discord.Interaction):
        state = await load_mmo_state(ctx)
        market_data = state.setdefault("marketplace", {})
        stats = market_data.setdefault("stats", {})
        user_stats = stats.get(str(interaction.user.id), {})
        gold_sunk = int(market_data.get("gold_sunk", 0) or 0)
        history_count = len(market_data.get("listing_history", []) or [])
        trade_log_count = len(market_data.get("trade_logs", []) or [])
        embed = discord.Embed(title="Marketplace Stats", color=0xF1C40F)
        embed.add_field(name="Global Gold Sunk", value=f"{gold_sunk:,} Gold", inline=False)
        embed.add_field(name="Market Sales Logged", value=str(history_count), inline=True)
        embed.add_field(name="Trades Logged", value=str(trade_log_count), inline=True)
        embed.add_field(name="Your Stats", value=(f"Listed: **{int(user_stats.get('items_listed', 0) or 0)}**\nSold: **{int(user_stats.get('items_sold', 0) or 0)}**\nBought: **{int(user_stats.get('items_bought', 0) or 0)}**\nGold Earned: **{int(user_stats.get('gold_earned', 0) or 0):,}**\nGold Spent: **{int(user_stats.get('gold_spent', 0) or 0):,}**\nTrades Created: **{int(user_stats.get('trades_created', 0) or 0)}**\nTrades Completed: **{int(user_stats.get('trades_completed', 0) or 0)}**"), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="marketeconomy", description="View MMO market inflation, scarcity, and drop-rate analytics")
    async def marketeconomy(interaction: discord.Interaction):
        state = await load_mmo_state(ctx)
        report = analyze_marketplace(state, catalog=GEAR_CATALOG)
        avg_prices = report.get("average_sale_price_by_rarity", {})
        notes = report.get("scarcity_notes", []) + report.get("drop_rate_notes", [])
        embed = discord.Embed(title="Marketplace Economy Dashboard", color=0xE67E22)
        embed.add_field(name="Inflation Pressure", value=str(report.get("inflation_pressure", "unknown")).title(), inline=True)
        embed.add_field(name="Active Market Value", value=f"{int(report.get('active_value', 0) or 0):,} Gold", inline=True)
        embed.add_field(name="Player Gold Supply", value=f"{int(report.get('total_player_gold', 0) or 0):,} Gold", inline=True)
        embed.add_field(name="Gold Sunk", value=f"{int(report.get('gold_sunk', 0) or 0):,} Gold", inline=True)
        embed.add_field(name="Active Listings", value=str(report.get("active_listings", 0)), inline=True)
        embed.add_field(name="Sales Logged", value=str(report.get("sold_count", 0)), inline=True)
        embed.add_field(name="Rarity Supply", value=_format_counter(report.get("rarity_supply", {})), inline=False)
        embed.add_field(name="Slot Supply", value=_format_counter(report.get("slot_supply", {})), inline=False)
        embed.add_field(name="Avg Sale Price by Rarity", value=_format_counter(avg_prices, empty="No completed sales yet"), inline=False)
        embed.add_field(name="Balance Notes", value="\n".join(f"• {note}" for note in notes[:8]) or "No major warnings yet.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="craftingpreview", description="Preview future crafting, salvage, upgrade, and reroll systems")
    async def craftingpreview(interaction: discord.Interaction):
        embed = discord.Embed(title="Future Crafting Systems", color=0x95A5A6)
        embed.description = "These systems are planned placeholders and are not active yet."
        embed.add_field(name="Item Flags", value="Soulbound, Untradeable, Raid-exclusive, Season-exclusive", inline=False)
        embed.add_field(name="Salvage", value="Break gear into Clash resources.", inline=False)
        embed.add_field(name="Craft", value="Spend Gold, Elixir, Ores, Dark Elixir, and Raid Medals to create targeted gear.", inline=False)
        embed.add_field(name="Upgrade", value="Raise item level and improve stat modifiers.", inline=False)
        embed.add_field(name="Reroll", value="Spend ores/gems to reroll stats or secondary bonuses.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="blackmarket", description="View rotating black market stock")
    async def blackmarket(interaction: discord.Interaction):
        items = rotate_black_market()
        embed = discord.Embed(title="Black Market Trader", description=format_black_market(items), color=0x9B59B6)
        await interaction.response.send_message(embed=embed)
