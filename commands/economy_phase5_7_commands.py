from __future__ import annotations

import discord
from discord import app_commands

from features.phase5.marketplace import (
    buy_listing,
    format_black_market,
    format_listing,
    get_active_listings,
    list_inventory_item,
    rotate_black_market,
)


from features.phase5.state import load_mmo_state, update_mmo_state



def register_economy_phase5_7_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _market():
        data = await safe_load_json(PHASE5_MARKET_FILE)

        if not isinstance(data, dict):
            data = {}

        data.setdefault("listings", [])
        return data

    @bot.tree.command(name="marketlist", description="List an item on the marketplace")
    @app_commands.describe(item_id="Item ID", price="Listing price")
    async def marketlist(
        interaction: discord.Interaction,
        item_id: str,
        price: int,
    ):
        def _update(state):
            list_inventory_item(
                state,
                str(interaction.user.id),
                item_id,
                price,
            )

            return state

        await update_json_file(PHASE5_MARKET_FILE, _update)

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

        await update_json_file(PHASE5_MARKET_FILE, _update)

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
