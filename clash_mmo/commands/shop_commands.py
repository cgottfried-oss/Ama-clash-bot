from __future__ import annotations

import random
import time

import discord
from discord import app_commands
from clash_mmo.game.state import load_mmo_state
from clash_mmo.game.state import load_mmo_state, update_mmo_state


SHOP_ITEM_UNLOCKS = {
    "training_potion": 3,
    "resource_potion": 3,
    "builder_potion": 4,
}

def register_shop_commands(bot, ctx):
    shop_items = ctx.SHOP_ITEMS
    loot_drop_styles = getattr(ctx, "LOOT_DROP_STYLES", [])
    loot_drop_file = ctx.LOOT_DROP_FILE

    safe_save_json = ctx.safe_save_json
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    get_inventory_text = ctx.get_inventory_text
    load_shop_data = ctx.load_shop_data
    consume_shop_item = ctx.consume_shop_item
    activate_shop_effect = ctx.activate_shop_effect
    load_loot_drop = ctx.load_loot_drop

    @bot.tree.command(name="shop", description="View the coin shop")
    async def shop(interaction: discord.Interaction):
        lines = []

        for item_key, item in shop_items.items():
            lines.append(
                f"**{item_key}** — {item['name']}\n"
                f"Cost: **{item['cost']}** coins\n"
                f"{item['description']}"
            )

        embed = discord.Embed(
            title="🛒 Coin Shop",
            description="\n\n".join(lines),
            color=0x9B59B6,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="buy", description="Buy an item from the coin shop")
    @app_commands.describe(item="The item key to buy")
    async def buy(interaction: discord.Interaction, item: str):
        item = item.strip().lower()

        if item not in shop_items:
            await interaction.response.send_message(
                "❌ Invalid item. Use `/shop` to view available items.",
                ephemeral=True,
            )
            return

        shop_item = shop_items[item]
        cost = shop_item["cost"]

        required_th = SHOP_ITEM_UNLOCKS.get(item)
        if required_th:
            state = await load_mmo_state(ctx)
            profile = state.get("players", {}).get(str(interaction.user.id), {})
            user_th = int(profile.get("town_hall", 1) or 1)
        
            if user_th < required_th:
                await interaction.response.send_message(
                    f"🔒 **{shop_item['name']}** unlocks at Town Hall **{required_th}**.\n"
                    f"Your current Town Hall: **{user_th}**.",
                    ephemeral=True,
                )
                return

        spend_result = {"ok": False, "balance": 0}

        def _spend_mmo_gold(state):
            if not isinstance(state, dict):
                state = {}
        
            players = state.setdefault("players", {})
            profile = players.setdefault(str(interaction.user.id), {})
            profile.setdefault("name", getattr(interaction.user, "display_name", interaction.user.name))
        
            current_gold = int(profile.get("gold", 0) or 0)
            spend_result["balance"] = current_gold
        
            if current_gold < cost:
                return state
        
            profile["gold"] = current_gold - int(cost)
            spend_result["balance"] = profile["gold"]
            spend_result["ok"] = True
        
            return state
        
        await update_mmo_state(ctx, _spend_mmo_gold)
        
        if not spend_result["ok"]:
            await interaction.response.send_message(
                f"❌ You need **{cost}** Gold to buy **{shop_item['name']}**.",
                ephemeral=True,
            )
            return

        await add_shop_item(str(interaction.user.id), item, 1)
        inventory_text = await get_inventory_text(str(interaction.user.id))

        embed = discord.Embed(
            title="✅ Purchase Successful",
            description=(
                f"You bought **{shop_item['name']}** for **{cost}** coins.\n\n"
                f"**New Balance:** {spend_result['balance']} coins"
            ),
            color=0x2ECC71,
        )
        embed.add_field(name="Inventory", value=inventory_text, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @buy.autocomplete("item")
    async def buy_item_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        current = current.lower()
        choices = []

        for item_key, item in shop_items.items():
            if current in item_key.lower() or current in item["name"].lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{item['name']} ({item_key}) - {item['cost']} coins",
                        value=item_key,
                    )
                )

        return choices[:25]

    @bot.tree.command(name="inventory", description="View your purchased shop items")
    async def inventory(interaction: discord.Interaction):
        inventory_text = await get_inventory_text(str(interaction.user.id))

        embed = discord.Embed(
            title="🎒 Your Inventory",
            description=inventory_text,
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="useitem", description="Use or activate an item from your inventory")
    @app_commands.describe(item="The item key to use")
    async def useitem(interaction: discord.Interaction, item: str):
        item = item.strip().lower()

        if item not in shop_items:
            await interaction.response.send_message(
                "❌ Invalid item. Use `/inventory` to see what you own.",
                ephemeral=True,
            )
            return

        shop_item = shop_items[item]
        item_type = shop_item.get("type")

        shop_data = await load_shop_data()
        inventory_data = (
            shop_data.get("users", {})
            .get(str(interaction.user.id), {})
            .get("inventory", {})
        )
        owned = int(inventory_data.get(item, 0) or 0)
        if owned <= 0:
            await interaction.response.send_message(
                f"❌ You do not own **{shop_item['name']}** yet. Buy it with `/buy {item}`.",
                ephemeral=True,
            )
            return

        if item == "drop_reroll":
            state = await load_mmo_state(ctx)
            profile = state.get("players", {}).get(str(interaction.user.id), {})
            cooldowns = profile.get("cooldowns", {}) if isinstance(profile, dict) else {}
            last_reroll = int(cooldowns.get("drop_reroll", 0) or 0)
            remaining = (10 * 60) - (int(time.time()) - last_reroll)

            if remaining > 0:
                await interaction.response.send_message(
                    f"⏳ Drop Reroll can only be used once every 10 minutes.\n"
                    f"Try again in **{remaining // 60}m {remaining % 60}s**.",
                    ephemeral=True,
                )
                return

            drop = await load_loot_drop()
            if not drop.get("active") or drop.get("claimed_by"):
                await interaction.response.send_message(
                    "❌ There is no active unclaimed loot drop to reroll right now.",
                    ephemeral=True,
                )
                return

            if not await consume_shop_item(str(interaction.user.id), "drop_reroll"):
                await interaction.response.send_message(
                    "❌ You do not have a Drop Reroll available.",
                    ephemeral=True,
                )
                return

            styles = loot_drop_styles or []
            if not styles:
                await interaction.response.send_message(
                    "❌ Loot drop styles are not available in this command context.",
                    ephemeral=True,
                )
                return

            old_reward = int(drop.get("reward", 0) or 0)
            style = random.choice(styles)
            new_reward = random.choice(style.get("rewards", [old_reward]))
            drop["reward"] = int(new_reward)
            drop["style"] = style.get("name", drop.get("style"))
            drop["rerolled_by"] = str(interaction.user.id)
            await safe_save_json(loot_drop_file, drop)

            def _stamp_reroll_cd(state):
                if not isinstance(state, dict):
                    state = {}
            
                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                profile.setdefault("name", getattr(interaction.user, "display_name", interaction.user.name))
            
                cooldowns_data = profile.setdefault("cooldowns", {})
                cooldowns_data["drop_reroll"] = int(time.time())
            
                return state
            
            await update_mmo_state(ctx, _stamp_reroll_cd)

            await interaction.response.send_message(
                f"🔁 **Drop Reroll used!** Active loot drop changed from **{old_reward}** to **{new_reward}** coins.",
                ephemeral=False,
            )
            return

        if item == "war_banner":
            duration_seconds = int(shop_item.get("duration_seconds", 3600) or 3600)
            result = await activate_shop_effect(str(interaction.user.id), "war_banner", duration_seconds)
            if not result.get("ok"):
                await interaction.response.send_message(
                    "❌ You need to own a War Banner before you can activate it.",
                    ephemeral=True,
                )
                return

            expires_at = int(result.get("expires_at", 0) or 0)
            minutes = max(1, (expires_at - int(time.time())) // 60)
            reward_pct = int(round((float(shop_item.get("war_reward_multiplier", 1.20) or 1.20) - 1) * 100))
            stat_pct = int(round((float(shop_item.get("war_stat_multiplier", 1.10) or 1.10) - 1) * 100))
            resist_pct = int(round(float(shop_item.get("steal_resistance", 0.15) or 0.15) * 100))
            await interaction.response.send_message(
                f"🏴 **War Banner activated!** For about **{minutes} minutes**, you get **+{reward_pct}% war coin rewards**, **+{stat_pct}% war stat/MVP score**, and steal attempts against you are **{resist_pct}% less likely** to succeed.",
                ephemeral=True,
            )
            return
            
        if item == "builder_potion":
            if not await consume_shop_item(str(interaction.user.id), "builder_potion"):
                await interaction.response.send_message(
                    "❌ You do not have a Builder Potion available.",
                    ephemeral=True,
                )
                return

            def _clear_raid_cooldowns(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                profile = players.setdefault(str(interaction.user.id), {})
                profile.setdefault("name", getattr(interaction.user, "display_name", interaction.user.name))

                cooldowns = profile.setdefault("cooldowns", {})
                cooldowns.pop("raid", None)
                cooldowns.pop("pve", None)
                cooldowns.pop("farm", None)
                
                pvp = profile.setdefault("pvp", {})
                pvp.pop("last_raiduser", None)

                return state

            await update_mmo_state(ctx, _clear_raid_cooldowns)

            await interaction.response.send_message(
                "🧪 **Builder Potion used!** Your raid cooldown has been cleared.",
                ephemeral=True,
            )
            return

        if item == "loot_shield":
            await interaction.response.send_message(
                "🛡️ **Loot Shield is passive.** Keep it in your inventory and it will automatically block the next raid-user attack against you.",
                ephemeral=True,
            )
            return

        if item_type in {"loot_bonus", "loot_gamble", "clutch_bonus", "mvp_bonus"}:
            await interaction.response.send_message(
                f"✅ **{shop_item['name']}** is passive and will trigger automatically when its condition happens.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"ℹ️ **{shop_item['name']}** does not have an active use yet.",
            ephemeral=True,
        )

    @useitem.autocomplete("item")
    async def useitem_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ):
        current = current.lower()
        shop_data = await load_shop_data()
        inventory_data = (
            shop_data.get("users", {})
            .get(str(interaction.user.id), {})
            .get("inventory", {})
        )
        choices = []
        for item_key, qty in inventory_data.items():
            item_data = shop_items.get(item_key)
            if not item_data:
                continue
            if current in item_key.lower() or current in item_data["name"].lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{item_data['name']} ({item_key}) x{qty}",
                        value=item_key,
                    )
                )
        return choices[:25]
