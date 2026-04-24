from __future__ import annotations

import html as html_lib
import re
import traceback
from datetime import datetime

import discord
from discord import app_commands
from playwright.async_api import async_playwright


def register_economy_commands(bot, ctx):
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID
    CLAN_CHAT_CHANNEL_ID = ctx.CLAN_CHAT_CHANNEL_ID
    LOOT_DROP_FILE = ctx.LOOT_DROP_FILE
    SHOP_ITEMS = ctx.SHOP_ITEMS
    LINKED_FILE = ctx.LINKED_FILE
    COIN_LEADERBOARD_IMAGE_PATH = ctx.COIN_LEADERBOARD_IMAGE_PATH

    safe_load_json = ctx.safe_load_json
    safe_save_json = ctx.safe_save_json
    normalize_linked_data = ctx.normalize_linked_data
    load_coins = ctx.load_coins
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    get_inventory_text = ctx.get_inventory_text
    create_loot_drop = ctx.create_loot_drop
    load_loot_drop = ctx.load_loot_drop
    schedule_next_loot_drop = ctx.schedule_next_loot_drop

    async def create_coin_leaderboard_image(top_users, guild=None):
        """Render the coin leaderboard as an HTML image so it matches the rest of the bot."""
        def _safe(value):
            return html_lib.escape(str(value if value is not None else ""))

        rows = []
        medals = ["🥇", "🥈", "🥉"]
        max_balance = max([int((data or {}).get("balance", 0) or 0) for _, data in top_users] + [1])

        for index, (user_id, data) in enumerate(top_users, start=1):
            data = data or {}
            medal = medals[index - 1] if index <= 3 else f"#{index}"
            balance_amount = int(data.get("balance", 0) or 0)
            lifetime_earned = int(data.get("lifetime_earned", 0) or 0)
            stored_name = str(data.get("name") or "Unknown")
            display_name = stored_name
            member = None
            if guild is not None:
                try:
                    member = guild.get_member(int(user_id))
                    if member is None:
                        member = await guild.fetch_member(int(user_id))
                except Exception:
                    member = None
            if member is not None:
                display_name = getattr(member, "display_name", None) or getattr(member, "name", None) or stored_name

            initials = "?"
            clean_parts = [part for part in re.split(r"\s+", display_name.strip()) if part]
            if clean_parts:
                initials = "".join(part[0] for part in clean_parts[:2]).upper()
            saved_note = "" if stored_name in ("Unknown", display_name) else " · Saved as " + _safe(stored_name)
            width_pct = max(4, int((balance_amount / max_balance) * 100)) if max_balance else 4
            rows.append(f"""
            <div class="leader-row">
                <div class="rank">{_safe(medal)}</div>
                <div class="avatar">{_safe(initials)}</div>
                <div class="main">
                    <div class="name">{_safe(display_name)}</div>
                    <div class="sub">Discord ID: {_safe(user_id)}{saved_note}</div>
                    <div class="bar"><div class="fill" style="width:{width_pct}%"></div></div>
                </div>
                <div class="coins"><strong>{balance_amount:,}</strong><span>coins</span><small>{lifetime_earned:,} lifetime</small></div>
            </div>
            """)

        total_balance = sum(int((data or {}).get("balance", 0) or 0) for _, data in top_users)
        top_balance = int((top_users[0][1] or {}).get("balance", 0) or 0) if top_users else 0
        rows_html = "".join(rows) if rows else '<div class="empty">No coin data yet.</div>'
        html_doc = f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><style>
    body {{ margin:0; background:#ececec; font-family:Arial, Helvetica, sans-serif; color:#202020; }}
    .container {{ width:1000px; min-height:760px; padding:30px 36px; box-sizing:border-box; background:white; border-radius:18px; box-shadow:0 10px 30px rgba(0,0,0,.08); }}
    .title {{ font-size:46px; font-weight:800; line-height:1; }} .subtitle {{ font-size:21px; color:#777; margin-top:8px; }}
    .summary {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin:22px 0 26px; }}
    .summary-card {{ background:#fafafa; border:1px solid #e5e5e5; border-radius:16px; padding:16px 18px; text-align:center; }}
    .summary-label {{ font-size:17px; color:#777; margin-bottom:4px; }} .summary-value {{ font-size:28px; font-weight:800; }}
    .board {{ border-top:1px solid #e3e3e3; padding-top:12px; }}
    .leader-row {{ display:grid; grid-template-columns:70px 64px 1fr 170px; gap:16px; align-items:center; padding:14px 0; border-bottom:1px solid #ececec; }}
    .rank {{ font-size:30px; font-weight:800; text-align:center; }}
    .avatar {{ width:58px; height:58px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:#f1f1f5; border:1px solid #ddd; font-size:22px; font-weight:800; color:#555; }}
    .name {{ font-size:26px; font-weight:800; color:#1f1f1f; }} .sub {{ font-size:15px; color:#777; margin-top:2px; }}
    .bar {{ width:100%; height:12px; background:#dfdfe4; border-radius:999px; overflow:hidden; margin-top:8px; }} .fill {{ height:100%; background:#e2c14d; border-radius:999px; }}
    .coins {{ text-align:right; font-size:19px; color:#555; }} .coins strong {{ display:block; font-size:30px; color:#202020; line-height:1; }} .coins span,.coins small {{ display:block; }} .coins small {{ font-size:14px; color:#777; margin-top:4px; }}
    .empty {{ font-size:24px; color:#777; text-align:center; padding:50px 0; }}
    </style></head><body><div class="container"><div class="title">🏆 Coin Leaderboard</div><div class="subtitle">Top active coin balances</div>
    <div class="summary"><div class="summary-card"><div class="summary-label">Players Shown</div><div class="summary-value">{len(top_users)}</div></div><div class="summary-card"><div class="summary-label">Top Balance</div><div class="summary-value">{top_balance:,}</div></div><div class="summary-card"><div class="summary-label">Shown Balance Total</div><div class="summary-value">{total_balance:,}</div></div></div>
    <div class="board">{rows_html}</div></div></body></html>"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = await browser.new_page(viewport={"width": 1000, "height": 900})
            await page.set_content(html_doc, wait_until="domcontentloaded")
            await page.wait_for_timeout(500)
            await page.screenshot(path=COIN_LEADERBOARD_IMAGE_PATH, full_page=True)
            await browser.close()
        return open(COIN_LEADERBOARD_IMAGE_PATH, "rb")


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
            buffer = await create_coin_leaderboard_image(top_users, guild=interaction.guild)
            await interaction.followup.send(file=discord.File(buffer, filename="coin_leaderboard.png"))
            return
        except Exception as exc:
            print(f"[COIN LEADERBOARD IMAGE ERROR] {exc}")
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

