from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.core.inventory import ensure_item_instance_id
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.marketplace import (
    cancel_market_listing,
    buy_market_listing,
    format_black_market,
    get_active_listings,
    rotate_black_market,
)
from clash_mmo.game.marketplace.service import (
    accept_trade_offer,
    create_market_listing,
    create_trade_offer,
    decline_trade_offer,
    expire_marketplace_entries,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state


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
        if not isinstance(item, dict):
            continue
        ensure_item_instance_id(item)
        out.append(item)
    return out


def _item_name(item: dict) -> str:
    item_id = str(item.get("item_id") or "unknown")
    gear = GEAR_CATALOG.get(item_id, {})
    return str(gear.get("name") or item_id.replace("_", " ").title())


def _short_id(value: str) -> str:
    value = str(value or "")
    return value.split("-")[0] if value else "unknown"


def _format_listing_line(listing: dict) -> str:
    item = listing.get("item_snapshot") or listing.get("escrow_item") or {}
    item_id = str(listing.get("item_id") or item.get("item_id") or "unknown")
    gear = GEAR_CATALOG.get(item_id, {})
    name = gear.get("name") or item_id.replace("_", " ").title()
    rarity = str(item.get("rarity") or gear.get("rarity") or "common").title()
    level = int(item.get("level", 1) or 1)
    price = int(listing.get("price", 0) or 0)
    seller_receives = int(listing.get("seller_receives", 0) or 0)
    listing_id = str(listing.get("listing_id") or "")
    expires_at = int(listing.get("expires_at", 0) or 0)
    expires_text = f" • Expires <t:{expires_at}:R>" if expires_at else ""

    return (
        f"`{_short_id(listing_id)}` **{name}** [{rarity}] Lv.{level}\n"
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


def register_market_commands(bot, ctx):
    async def item_instance_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
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

            label = f"{name} [{rarity}] Lv.{level} • {_short_id(instance_id)}"
            choices.append(app_commands.Choice(name=label[:100], value=instance_id[:100]))

            if len(choices) >= 25:
                break

        return choices

    async def listing_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
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

            label = f"{_short_id(listing_id)} • {item_name} • {price:,} Gold"
            choices.append(app_commands.Choice(name=label[:100], value=listing_id[:100]))

            if len(choices) >= 25:
                break

        return choices

    async def trade_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
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

    @bot.tree.command(name="marketsell", description="List one of your gear items on the player marketplace")
    @app_commands.describe(item="Choose an item from your inventory", price="Listing price in Gold")
    @app_commands.autocomplete(item=item_instance_autocomplete)
    async def marketsell(interaction: discord.Interaction, item: str, price: int):
        result_box = {}

        def _update(state):
            result = create_market_listing(
                state,
                str(interaction.user.id),
                item,
                price,
                now=int(ctx.now()),
            )
            result_box.update(result)
            return state

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not list item.')}", ephemeral=True)
            return

        listing = result_box["listing"]
        listed_item = listing.get("item_snapshot") or listing.get("escrow_item") or {}

        await interaction.response.send_message(
            f"📦 Listed **{_item_name(listed_item)}** for **{int(price):,} Gold**.\n"
            f"Listing ID: `{_short_id(listing['listing_id'])}`"
        )

    @bot.tree.command(name="market", description="Browse active player marketplace listings")
    async def market(interaction: discord.Interaction):
        state = await load_mmo_state(ctx)

        def _update(state_data):
            expire_marketplace_entries(state_data, now=int(ctx.now()))
            return state_data

        await update_mmo_state(ctx, _update)
        state = await load_mmo_state(ctx)
        listings = get_active_listings(state)

        if not listings:
            await interaction.response.send_message("Marketplace is empty.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Player Marketplace",
            description="\n\n".join(_format_listing_line(listing) for listing in listings[:10]),
            color=0x2ECC71,
        )
        embed.set_footer(text="Use /marketbuy with the listing ID to purchase an item.")

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="marketbuy", description="Buy a player marketplace listing")
    @app_commands.describe(listing="Marketplace listing ID")
    @app_commands.autocomplete(listing=listing_autocomplete)
    async def marketbuy(interaction: discord.Interaction, listing: str):
        result_box = {}

        def _update(state):
            result = buy_market_listing(
                state,
                str(interaction.user.id),
                listing,
                now=int(ctx.now()),
            )
            result_box.update(result)
            return state

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not buy listing.')}", ephemeral=True)
            return

        bought_item = result_box.get("item", {})
        price = int(result_box.get("price", 0) or 0)

        await interaction.response.send_message(
            f"🛒 Purchased **{_item_name(bought_item)}** for **{price:,} Gold**."
        )

    @bot.tree.command(name="marketcancel", description="Cancel one of your active marketplace listings")
    @app_commands.describe(listing="Marketplace listing ID")
    @app_commands.autocomplete(listing=listing_autocomplete)
    async def marketcancel(interaction: discord.Interaction, listing: str):
        result_box = {}

        def _update(state):
            result = cancel_market_listing(
                state,
                str(interaction.user.id),
                listing,
                now=int(ctx.now()),
            )
            result_box.update(result)
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
            result = create_trade_offer(
                state,
                str(interaction.user.id),
                str(user.id),
                item,
                requested_gold,
                now=int(ctx.now()),
            )
            result_box.update(result)
            return state

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not create trade.')}", ephemeral=True)
            return

        trade = result_box["trade"]
        item_data = trade.get("sender_item") or {}
        await interaction.response.send_message(
            f"🤝 Trade offered to {user.mention}: **{_item_name(item_data)}** for **{int(requested_gold or 0):,} Gold**.\n"
            f"Trade ID: `{_short_id(trade['trade_id'])}`"
        )

    @bot.tree.command(name="trades", description="View your pending player trades")
    async def trades(interaction: discord.Interaction):
        state = await load_mmo_state(ctx)

        def _update(state_data):
            expire_marketplace_entries(state_data, now=int(ctx.now()))
            return state_data

        await update_mmo_state(ctx, _update)
        state = await load_mmo_state(ctx)
        market = state.setdefault("marketplace", {})
        viewer_id = str(interaction.user.id)
        pending = [
            trade for trade in market.setdefault("trades", [])
            if trade.get("status") == "pending" and viewer_id in {str(trade.get("sender_id")), str(trade.get("target_id"))}
        ]

        if not pending:
            await interaction.response.send_message("You have no pending trades.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Pending Trades",
            description="\n\n".join(_format_trade_line(trade, viewer_id=viewer_id) for trade in pending[:10]),
            color=0x3498DB,
        )
        embed.set_footer(text="Use /tradeaccept or /tradedecline with the trade ID.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="tradeaccept", description="Accept a pending trade sent to you")
    @app_commands.describe(trade="Trade ID")
    @app_commands.autocomplete(trade=trade_autocomplete)
    async def tradeaccept(interaction: discord.Interaction, trade: str):
        result_box = {}

        def _update(state):
            result = accept_trade_offer(
                state,
                str(interaction.user.id),
                trade,
                now=int(ctx.now()),
            )
            result_box.update(result)
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
            result = decline_trade_offer(
                state,
                str(interaction.user.id),
                trade,
                now=int(ctx.now()),
            )
            result_box.update(result)
            return state

        await update_mmo_state(ctx, _update)

        if not result_box.get("ok"):
            await interaction.response.send_message(f"❌ {result_box.get('error', 'Could not decline trade.')}", ephemeral=True)
            return

        await interaction.response.send_message("❌ Trade declined. The item was returned to the sender.", ephemeral=True)

    @bot.tree.command(name="marketstats", description="View marketplace economy stats")
    async def marketstats(interaction: discord.Interaction):
        state = await load_mmo_state(ctx)
        market = state.setdefault("marketplace", {})
        stats = market.setdefault("stats", {})
        user_stats = stats.get(str(interaction.user.id), {})
        gold_sunk = int(market.get("gold_sunk", 0) or 0)
        history_count = len(market.get("listing_history", []) or [])
        trade_log_count = len(market.get("trade_logs", []) or [])

        embed = discord.Embed(title="Marketplace Stats", color=0xF1C40F)
        embed.add_field(name="Global Gold Sunk", value=f"{gold_sunk:,} Gold", inline=False)
        embed.add_field(name="Market Sales Logged", value=str(history_count), inline=True)
        embed.add_field(name="Trades Logged", value=str(trade_log_count), inline=True)
        embed.add_field(
            name="Your Stats",
            value=(
                f"Listed: **{int(user_stats.get('items_listed', 0) or 0)}**\n"
                f"Sold: **{int(user_stats.get('items_sold', 0) or 0)}**\n"
                f"Bought: **{int(user_stats.get('items_bought', 0) or 0)}**\n"
                f"Gold Earned: **{int(user_stats.get('gold_earned', 0) or 0):,}**\n"
                f"Gold Spent: **{int(user_stats.get('gold_spent', 0) or 0):,}**\n"
                f"Trades Created: **{int(user_stats.get('trades_created', 0) or 0)}**\n"
                f"Trades Completed: **{int(user_stats.get('trades_completed', 0) or 0)}**"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="blackmarket", description="View rotating black market stock")
    async def blackmarket(interaction: discord.Interaction):
        items = rotate_black_market()

        embed = discord.Embed(
            title="Black Market Trader",
            description=format_black_market(items),
            color=0x9B59B6,
        )

        await interaction.response.send_message(embed=embed)
