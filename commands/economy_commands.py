from __future__ import annotations

import html as html_lib
import re
import traceback
import random
import time
from datetime import datetime
from pathlib import Path

import discord
from discord import app_commands
from playwright.async_api import async_playwright


def register_economy_commands(bot, ctx):
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID
    CLAN_CHAT_CHANNEL_ID = ctx.CLAN_CHAT_CHANNEL_ID
    LOOT_DROP_FILE = ctx.LOOT_DROP_FILE
    SHOP_ITEMS = ctx.SHOP_ITEMS
    LOOT_DROP_STYLES = getattr(ctx, "LOOT_DROP_STYLES", [])
    LINKED_FILE = ctx.LINKED_FILE
    COIN_LEADERBOARD_IMAGE_PATH = ctx.COIN_LEADERBOARD_IMAGE_PATH

    safe_load_json = ctx.safe_load_json
    safe_save_json = ctx.safe_save_json
    normalize_linked_data = ctx.normalize_linked_data
    load_coins = ctx.load_coins
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    get_inventory_text = ctx.get_inventory_text
    load_shop_data = ctx.load_shop_data
    consume_shop_item = ctx.consume_shop_item
    equip_shop_item = ctx.equip_shop_item
    activate_shop_effect = ctx.activate_shop_effect
    get_active_shop_effects = ctx.get_active_shop_effects
    steal_coins = ctx.steal_coins
    create_loot_drop = ctx.create_loot_drop
    load_loot_drop = ctx.load_loot_drop
    schedule_next_loot_drop = ctx.schedule_next_loot_drop

    async def create_coin_leaderboard_image(top_users, guild=None):
        def _safe(v):
            return html_lib.escape(str(v if v is not None else ""), quote=True)
    
        # 🔥 Rank tracking (for arrows)
        STATE_FILE = str(Path(COIN_LEADERBOARD_IMAGE_PATH).with_name("coin_lb_state.json"))
        prev = await safe_load_json(STATE_FILE)
        prev_ranks = prev.get("ranks", {}) if isinstance(prev, dict) else {}
    
        rows = []
        medals = ["🥇", "🥈", "🥉"]
        rank_classes = ["gold", "silver", "bronze"]
    
        max_balance = max([int((d or {}).get("balance", 0) or 0) for _, d in top_users] + [1])
    
        for i, (user_id, data) in enumerate(top_users, start=1):
            data = data or {}
            medal = medals[i-1] if i <= 3 else f"#{i}"
            rank_class = rank_classes[i-1] if i <= 3 else "standard"
    
            bal = int(data.get("balance", 0) or 0)
            lifetime = int(data.get("lifetime_earned", 0) or 0)
    
            name = str(data.get("name") or "Unknown")
            display = name
            avatar_html = ""
    
            # ✅ REAL DISCORD AVATAR
            if guild:
                try:
                    m = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
                    if m:
                        display = m.display_name
                        avatar_url = m.display_avatar.replace(size=128).url
                        avatar_html = f'<img class="avatar-img" src="{_safe(avatar_url)}">'
                except:
                    pass
    
            if not avatar_html:
                initials = "".join([p[0] for p in display.split()[:2]]).upper() or "?"
                avatar_html = f"<span>{_safe(initials)}</span>"
    
            # 🔥 Rank change arrows
            old = prev_ranks.get(str(user_id))
            if old:
                if old > i:
                    delta = f'<span class="up">▲{old-i}</span>'
                elif old < i:
                    delta = f'<span class="down">▼{i-old}</span>'
                else:
                    delta = '<span class="same">◆</span>'
            else:
                delta = '<span class="new">NEW</span>'
    
            # 🔥 Milestone glow
            if bal >= 4000:
                glow = "legendary"
            elif bal >= 3000:
                glow = "elite"
            elif bal >= 2000:
                glow = "epic"
            else:
                glow = "normal"
    
            pct = int((bal / max_balance) * 100)
    
            rows.append(f"""
            <div class="row {rank_class} {glow}">
                <div class="rank">{medal}{delta}</div>
                <div class="avatar">{avatar_html}</div>
                <div class="main">
                    <div class="name">{_safe(display)}</div>
                    <div class="bar">
                        <div class="fill" style="width:{pct}%">
                            <div class="shimmer"></div>
                        </div>
                    </div>
                </div>
                <div class="coins">
                    <b>{bal:,}</b>
                    <small>{lifetime:,}</small>
                </div>
            </div>
            """)
    
        html = f"""
        <html><style>
        body {{background:#1e2433;color:white;font-family:sans-serif}}
        .row {{display:flex;align-items:center;padding:12px;margin:6px;background:#2b334a;border-radius:12px}}
        .rank {{width:80px}}
        .avatar {{width:50px;height:50px;border-radius:50%;overflow:hidden}}
        .avatar-img {{width:100%;height:100%}}
        .bar {{height:10px;background:#111;border-radius:10px;margin-top:6px;position:relative}}
        .fill {{height:100%;background:linear-gradient(90deg,#58d8ff,#ffe66d);position:relative}}
        .shimmer {{position:absolute;width:40px;height:100%;background:linear-gradient(90deg,transparent,white,transparent);animation:shimmer 2s infinite}}
        @keyframes shimmer {{0%{{left:-40px}}100%{{left:100%}}}}
        .legendary {{box-shadow:0 0 15px gold}}
        .elite {{box-shadow:0 0 10px cyan}}
        .epic {{box-shadow:0 0 10px purple}}
        </style>
        {"".join(rows)}
        </html>
        """
    
        path = Path(COIN_LEADERBOARD_IMAGE_PATH)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width":1000,"height":1300})
        await page.set_content(html)
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(path))
        await browser.close()

    await safe_save_json(STATE_FILE, {
        "ranks": {str(uid): idx for idx,(uid,_) in enumerate(top_users,1)}
    })

    return discord.File(str(path), filename="coin_leaderboard.png")


    @bot.tree.command(name="spawnloot", description="Manually spawn a loot drop in clan chat")
    async def spawnloot(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ This command must be used in a server.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Could not verify your server roles.",
                ephemeral=True,
            )
            return

        if not any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
            return

        created = await create_loot_drop()
        if not created:
            await interaction.response.send_message(
                "There is already an active loot drop.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ Loot drop spawned in clan chat.",
            ephemeral=True,
        )


    @bot.tree.command(name="balance", description="View your coin balance")
    async def balance(interaction: discord.Interaction):
        linked_raw = await safe_load_json(LINKED_FILE)
        linked = normalize_linked_data(linked_raw)
        user_entries = linked.get(str(interaction.user.id), [])

        if not user_entries:
            await interaction.response.send_message(
                "❌ You have not linked a Clash account yet. Use `/link` first.",
                ephemeral=True,
            )
            return

        stored = await load_coins()
        user_data = stored.get("users", {}).get(str(interaction.user.id), {})
        balance_amount = user_data.get("balance", 0)
        lifetime_earned = user_data.get("lifetime_earned", 0)

        account_list = ", ".join(
            f"{entry.get('name', 'Unknown')} ({entry.get('tag', 'Unknown')})"
            for entry in user_entries
        )

        embed = discord.Embed(
            title="💰 Coin Balance",
            color=0xF1C40F,
        )
        embed.add_field(name="Balance", value=str(balance_amount), inline=True)
        embed.add_field(name="Lifetime Earned", value=str(lifetime_earned), inline=True)
        embed.add_field(name="Linked Accounts", value=account_list or "None", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="coinleaderboard", description="View the top coin earners")
    async def coinleaderboard(interaction: discord.Interaction):
        stored = await load_coins()
        users = stored.get("users", {})

        if not users:
            await interaction.response.send_message("No coin data yet. Finish a war first.", ephemeral=True)
            return

        top_users = sorted(users.items(), key=lambda item: item[1].get("balance", 0), reverse=True)[:10]
        await interaction.response.defer()
        try:
            file = await create_coin_leaderboard_image(top_users, guild=interaction.guild)
            await interaction.followup.send(file=file)
            return
        except Exception as exc:
            print(f"[COIN LEADERBOARD IMAGE ERROR] {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc()

        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for index, (user_id, data) in enumerate(top_users, start=1):
            medal = medals[index - 1] if index <= 3 else f"#{index}"
            balance_amount = data.get("balance", 0)
            name = data.get("name", "Unknown")
            member = interaction.guild.get_member(int(user_id)) if interaction.guild else None
            display_name = member.display_name if member else f"<@{user_id}>"
            lines.append(f"{medal} {display_name} — **{balance_amount}** coins ({name})")

        embed = discord.Embed(
            title="🏆 Coin Leaderboard",
            description="\n".join(lines) if lines else "No coin data yet.",
            color=0xF1C40F,
        )
        embed.set_footer(text="Image render failed, so this fallback embed is being shown.")
        await interaction.followup.send(embed=embed)


    @bot.tree.command(name="dropstatus", description="View the current loot drop status")
    async def dropstatus(interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Could not verify your server roles.",
                ephemeral=True,
            )
            return

        is_leader = any(
            role.id in (LEADER_ROLE_ID, CO_LEADER_ROLE_ID)
            for role in interaction.user.roles
        )

        if not is_leader:
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
            return

        drop = await load_loot_drop()

        active = drop.get("active", False)
        style = drop.get("style") or "None"
        reward = drop.get("reward", 0)
        claimed_by = drop.get("claimed_by")
        next_drop_at_raw = drop.get("next_drop_at")
        created_at_raw = drop.get("created_at")

        embed = discord.Embed(
            title="📦 Loot Drop Status",
            color=0x3498DB,
        )

        embed.add_field(
            name="Active Drop",
            value="Yes" if active else "No",
            inline=True,
        )
        embed.add_field(
            name="Style",
            value=str(style).replace("_", " ").title(),
            inline=True,
        )
        embed.add_field(
            name="Reward",
            value=f"{reward} coins" if reward else "None",
            inline=True,
        )

        if claimed_by:
            embed.add_field(
                name="Last Claimed By",
                value=f"<@{claimed_by}>",
                inline=True,
            )
        else:
            embed.add_field(
                name="Last Claimed By",
                value="Nobody yet",
                inline=True,
            )

        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(created_at_raw)
                embed.add_field(
                    name="Created At",
                    value=discord.utils.format_dt(created_at, style="R"),
                    inline=True,
                )
            except Exception:
                embed.add_field(
                    name="Created At",
                    value=created_at_raw,
                    inline=True,
                )
        else:
            embed.add_field(
                name="Created At",
                value="N/A",
                inline=True,
            )

        if next_drop_at_raw:
            try:
                next_drop_at = datetime.fromisoformat(next_drop_at_raw)
                embed.add_field(
                    name="Next Scheduled Drop",
                    value=f"{discord.utils.format_dt(next_drop_at, style='F')}\n({discord.utils.format_dt(next_drop_at, style='R')})",
                    inline=False,
                )
            except Exception:
                embed.add_field(
                    name="Next Scheduled Drop",
                    value=str(next_drop_at_raw),
                    inline=False,
                )
        else:
            embed.add_field(
                name="Next Scheduled Drop",
                value="Not scheduled yet",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="resetdrop", description="Reset the current loot drop state")
    async def resetdrop(interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Could not verify your server roles.",
                ephemeral=True,
            )
            return

        is_leader = any(
            role.id in (LEADER_ROLE_ID, CO_LEADER_ROLE_ID)
            for role in interaction.user.roles
        )

        if not is_leader:
            await interaction.response.send_message(
                "❌ You do not have permission to use this command.",
                ephemeral=True,
            )
            return

        drop = await load_loot_drop()

        drop["active"] = False
        drop["drop_id"] = None
        drop["channel_id"] = CLAN_CHAT_CHANNEL_ID
        drop["reward"] = 0
        drop["style"] = None
        drop["claimed_by"] = None
        drop["message_id"] = None
        drop["created_at"] = None
        drop["next_drop_at"] = None

        await safe_save_json(LOOT_DROP_FILE, drop)
        await schedule_next_loot_drop()

        updated = await load_loot_drop()
        next_drop_at_raw = updated.get("next_drop_at")

        next_text = "Scheduled"
        if next_drop_at_raw:
            try:
                next_drop_at = datetime.fromisoformat(next_drop_at_raw)
                next_text = f"{discord.utils.format_dt(next_drop_at, style='F')} ({discord.utils.format_dt(next_drop_at, style='R')})"
            except Exception:
                next_text = str(next_drop_at_raw)

        await interaction.response.send_message(
            f"✅ Loot drop state reset.\nNext drop: {next_text}",
            ephemeral=True,
        )


    @bot.tree.command(name="shop", description="View the coin shop")
    async def shop(interaction: discord.Interaction):
        lines = []

        for item_key, item in SHOP_ITEMS.items():
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

        if item not in SHOP_ITEMS:
            await interaction.response.send_message(
                "❌ Invalid item. Use `/shop` to view available items.",
                ephemeral=True,
            )
            return

        shop_item = SHOP_ITEMS[item]
        cost = shop_item["cost"]

        spend_result = await spend_coins(str(interaction.user.id), cost)
        if not spend_result["ok"]:
            await interaction.response.send_message(
                f"❌ You need **{cost}** coins to buy **{shop_item['name']}**.",
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

        for item_key, item in SHOP_ITEMS.items():
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

        if item not in SHOP_ITEMS:
            await interaction.response.send_message(
                "❌ Invalid item. Use `/inventory` to see what you own.",
                ephemeral=True,
            )
            return

        shop_item = SHOP_ITEMS[item]
        item_type = shop_item.get("type")

        shop_data = await load_shop_data()
        inventory = (
            shop_data.get("users", {})
            .get(str(interaction.user.id), {})
            .get("inventory", {})
        )
        owned = int(inventory.get(item, 0) or 0)
        if owned <= 0:
            await interaction.response.send_message(
                f"❌ You do not own **{shop_item['name']}** yet. Buy it with `/buy {item}`.",
                ephemeral=True,
            )
            return

        if item == "drop_reroll":
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

            styles = LOOT_DROP_STYLES or []
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
            await safe_save_json(LOOT_DROP_FILE, drop)

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

        if item == "loot_shield":
            await interaction.response.send_message(
                "🛡️ **Loot Shield is passive.** Keep it in your inventory and it will automatically block the next `/steal` attempt against you.",
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
        inventory = (
            shop_data.get("users", {})
            .get(str(interaction.user.id), {})
            .get("inventory", {})
        )
        choices = []
        for item_key, qty in inventory.items():
            item = SHOP_ITEMS.get(item_key)
            if not item:
                continue
            if current in item_key.lower() or current in item["name"].lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{item['name']} ({item_key}) x{qty}",
                        value=item_key,
                    )
                )
        return choices[:25]


    @bot.tree.command(name="steal", description="Try to steal coins from another user")
    @app_commands.describe(target="The user you want to try stealing coins from")
    @app_commands.checks.cooldown(1, 300.0, key=lambda i: i.user.id)
    async def steal(interaction: discord.Interaction, target: discord.Member):
        if target.bot:
            await interaction.response.send_message("❌ You cannot steal from bots.", ephemeral=True)
            return

        if target.id == interaction.user.id:
            await interaction.response.send_message("❌ You cannot steal from yourself.", ephemeral=True)
            return

        result = await steal_coins(
            thief_id=str(interaction.user.id),
            thief_name=getattr(interaction.user, "display_name", interaction.user.name),
            victim_id=str(target.id),
            victim_name=getattr(target, "display_name", target.name),
        )

        if result.get("reason") == "shielded":
            await interaction.response.send_message(
                f"🛡️ {target.mention}'s **Loot Shield** blocked the steal attempt and was consumed!",
                ephemeral=False,
            )
            return

        if result.get("reason") == "victim_broke":
            await interaction.response.send_message(
                f"❌ {target.mention} has no coins to steal.",
                ephemeral=True,
            )
            return

        banner_note = " 🏴 War Banner made the steal harder." if result.get("war_banner_protected") else ""

        if result.get("success"):
            await interaction.response.send_message(
                f"🦹 {interaction.user.mention} stole **{result['amount']}** coins from {target.mention}! "
                f"New balance: **{result['thief_balance']}** coins.{banner_note}",
                ephemeral=False,
            )
            return

        await interaction.response.send_message(
            f"🚨 {interaction.user.mention} got caught trying to steal from {target.mention} "
            f"and paid **{result.get('penalty', 0)}** coins as a penalty.{banner_note}",
            ephemeral=False,
        )


    @steal.error
    async def steal_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ You can try stealing again in **{int(error.retry_after)}** seconds.",
                ephemeral=True,
            )
            return
        raise error

