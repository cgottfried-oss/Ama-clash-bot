from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.marketplace import (
    buy_listing,
    format_black_market,
    format_listing,
    get_active_listings,
    list_inventory_item,
    rotate_black_market,
)


from clash_mmo.game.state import load_mmo_state, update_mmo_state


def _inventory_items_for_user(state, user_id: str):
    players = state.get("players", {})
    player = players.get(user_id, {})
    inventory = player.get("inventory", {})

    if isinstance(inventory, dict):
        return [
            (str(item_id), qty)
            for item_id, qty in inventory.items()
            if isinstance(qty, int) and qty > 0
        ]

    if isinstance(inventory, list):
        return [
            (str(item_id), 1)
            for item_id in inventory
        ]

    return []


def register_market_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _market():
        data = await load_mmo_state(ctx)
    
        market = data.setdefault("marketplace", {})
    
        market.setdefault("listings", [])
        market.setdefault("black_market", {})
    
        return market

    async def item_id_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        state = await load_mmo_state(ctx)
        items = _inventory_items_for_user(state, str(interaction.user.id))

        current = current.lower().strip()
        choices = []

        for item_id, qty in items:
            if current and current not in item_id.lower():
                continue

            label = f"{item_id} x{qty}"
            choices.append(
                app_commands.Choice(
                    name=label[:100],
                    value=item_id[:100],
                )
            )

            if len(choices) >= 25:
                break

        return choices

    @bot.tree.command(name="marketlist", description="List an item on the marketplace")
    @app_commands.describe(item_id="Choose an item from your inventory", price="Listing price")
    @app_commands.autocomplete(item_id=item_id_autocomplete)
    async def marketlist(
        interaction: discord.Interaction,
        item_id: str,
        price: int,
    ):
        state = await load_mmo_state(ctx)
        owned_items = dict(_inventory_items_for_user(state, str(interaction.user.id)))

        if item_id not in owned_items:
            await interaction.response.send_message(
                "You do not have that item in your inventory. Use `/inventory` to check what you can list.",
                ephemeral=True,
            )
            return

        if price <= 0:
            await interaction.response.send_message(
                "Listing price must be greater than 0.",
                ephemeral=True,
            )
            return

        def _update(state):
            list_inventory_item(
                state,
                str(interaction.user.id),
                item_id,
                price,
            )

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"📦 Listed {item_id} for {price:,} Gold"
        )

    @bot.tree.command(name="marketbrowse", description="Browse marketplace listings")
    async def marketbrowse(interaction: discord.Interaction):
        market = await _market()

        listings = get_active_listings(market)

        if not listings:
            await interaction.response.send_message(
                "Marketplace is empty.",
                ephemeral=True,
            )
            return

        lines = [
            format_listing(listing)
            for listing in listings[:10]
        ]

        embed = discord.Embed(
            title="Marketplace Listings",
            description="\n\n".join(lines),
            color=0x2ECC71,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="buylisting", description="Buy a marketplace listing")
    @app_commands.describe(listing_id="Marketplace listing ID")
    async def buylisting(interaction: discord.Interaction, listing_id: str):
        market = await _market()

        result = buy_listing(
            market,
            listing_id,
            str(interaction.user.id),
        )

        if not result["ok"]:
            await interaction.response.send_message(
                result["error"],
                ephemeral=True,
            )
            return

        def _update(state):
            state.update(market)
            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"🛒 Purchased {result['listing']['item_id']}"
        )

    @bot.tree.command(name="blackmarket", description="View rotating black market stock")
    async def blackmarket(interaction: discord.Interaction):
        items = rotate_black_market()

        embed = discord.Embed(
            title="Black Market Trader",
            description=format_black_market(items),
            color=0x9B59B6,
        )

        await interaction.response.send_message(embed=embed)
