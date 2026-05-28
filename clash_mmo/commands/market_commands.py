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
from clash_mmo.game.marketplace.service import create_market_listing
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

    return (
        f"`{_short_id(listing_id)}` **{name}** [{rarity}] Lv.{level}\n"
        f"Price: **{price:,} Gold** • Seller receives: **{seller_receives:,}**"
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

    @bot.tree.command(name="blackmarket", description="View rotating black market stock")
    async def blackmarket(interaction: discord.Interaction):
        items = rotate_black_market()

        embed = discord.Embed(
            title="Black Market Trader",
            description=format_black_market(items),
            color=0x9B59B6,
        )

        await interaction.response.send_message(embed=embed)
