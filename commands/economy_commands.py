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
        """Render the coin leaderboard as an HTML image so it matches the rest of the bot."""
        def _safe(value):
            return html_lib.escape(str(value if value is not None else ""))

        rows = []
        medals = ["🥇", "🥈", "🥉"]
        rank_classes = ["gold", "silver", "bronze"]
        max_balance = max([int((data or {}).get("balance", 0) or 0) for _, data in top_users] + [1])

        for index, (user_id, data) in enumerate(top_users, start=1):
            data = data or {}
            medal = medals[index - 1] if index <= 3 else f"#{index}"
            rank_class = rank_classes[index - 1] if index <= 3 else "standard"
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
            crown = '<div class="crown">KING</div>' if index == 1 else ""
            rows.append(f"""
            <div class="leader-row {rank_class}">
                <div class="rank-badge"><div class="rank">{_safe(medal)}</div>{crown}</div>
                <div class="avatar {rank_class}">{_safe(initials)}</div>
                <div class="main">
                    <div class="name">{_safe(display_name)}</div>
                    <div class="sub">Discord ID: {_safe(user_id)}{saved_note}</div>
                    <div class="bar"><div class="fill {rank_class}" style="width:{width_pct}%"></div></div>
                </div>
                <div class="coins"><strong>{balance_amount:,}</strong><span>coins</span><small>{lifetime_earned:,} lifetime</small></div>
            </div>
            """)

        total_balance = sum(int((data or {}).get("balance", 0) or 0) for _, data in top_users)
        top_balance = int((top_users[0][1] or {}).get("balance", 0) or 0) if top_users else 0
        avg_balance = int(total_balance / max(1, len(top_users))) if top_users else 0
        rows_html = "".join(rows) if rows else '<div class="empty">No coin data yet.</div>'
        html_doc = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
body {{ margin:0; background:#8a98b5; font-family:Arial, Helvetica, sans-serif; color:#fff; }}
.shell {{ width:1000px; box-sizing:border-box; padding:28px; background:radial-gradient(circle at 22% 8%, rgba(151,176,231,.52), transparent 34%), linear-gradient(135deg,#56647f 0%,#34415d 48%,#242e49 100%); border:3px solid rgba(199,213,244,.46); border-radius:28px; box-shadow:0 24px 52px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.22); position:relative; overflow:hidden; }}
.shell:before {{ content:""; position:absolute; inset:0; background:linear-gradient(90deg, rgba(255,255,255,.10), transparent 18%, transparent 82%, rgba(255,255,255,.08)); pointer-events:none; }}
.header {{ position:relative; padding:25px 28px; border-radius:22px; background:linear-gradient(180deg,#596b99 0%,#263456 100%); border:2px solid rgba(166,187,241,.42); box-shadow:inset 0 2px 0 rgba(255,255,255,.16), 0 10px 22px rgba(0,0,0,.30); }}
.title-row {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
.title {{ font-size:48px; font-weight:950; line-height:1; text-shadow:0 3px 3px rgba(0,0,0,.48); letter-spacing:.2px; }}
.subtitle {{ font-size:18px; font-weight:800; color:rgba(255,255,255,.84); margin-top:8px; }}
.hero-badge {{ min-width:160px; text-align:center; padding:12px 14px; border-radius:16px; background:linear-gradient(180deg, rgba(255,224,111,.26), rgba(92,61,11,.22)); border:1px solid rgba(255,230,109,.44); box-shadow:0 0 20px rgba(255,215,80,.12), inset 0 1px 0 rgba(255,255,255,.16); }}
.hero-badge .label {{ color:rgba(255,255,255,.74); font-size:12px; font-weight:900; text-transform:uppercase; letter-spacing:.8px; }}
.hero-badge .value {{ font-size:24px; font-weight:950; color:#ffe66d; text-shadow:0 2px 2px rgba(0,0,0,.45); }}
.panel {{ position:relative; margin-top:22px; padding:20px; border-radius:22px; background:linear-gradient(180deg,rgba(57,72,112,.90),rgba(30,41,74,.94)); border:2px solid rgba(126,146,198,.30); box-shadow:inset 0 1px 0 rgba(255,255,255,.10), 0 12px 28px rgba(0,0,0,.28); }}
.summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:18px; }}
.summary-card {{ background:linear-gradient(180deg,rgba(30,42,78,.96),rgba(21,30,60,.99)); border:1px solid rgba(148,163,220,.26); border-radius:17px; padding:14px 16px; text-align:center; box-shadow:inset 0 1px 0 rgba(255,255,255,.11),0 8px 16px rgba(0,0,0,.20); }}
.summary-label {{ font-size:13px; color:rgba(255,255,255,.66); margin-bottom:5px; font-weight:900; text-transform:uppercase; letter-spacing:.35px; }}
.summary-value {{ font-size:27px; font-weight:950; color:#fff; text-shadow:0 2px 2px rgba(0,0,0,.40); }}
.board {{ display:flex; flex-direction:column; gap:10px; }}
.leader-row {{ display:grid; grid-template-columns:82px 70px 1fr 172px; gap:16px; align-items:center; padding:13px 14px; border-radius:18px; background:linear-gradient(180deg,rgba(24,34,66,.97),rgba(18,27,54,.98)); border:1px solid rgba(148,163,220,.24); box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 8px 16px rgba(0,0,0,.21); position:relative; overflow:hidden; }}
.leader-row.gold {{ border-color:rgba(255,230,109,.62); box-shadow:0 0 24px rgba(255,209,58,.22), inset 0 1px 0 rgba(255,255,255,.16),0 10px 20px rgba(0,0,0,.25); background:linear-gradient(180deg,rgba(57,50,91,.98),rgba(27,31,61,.99)); }}
.leader-row.silver {{ border-color:rgba(224,232,255,.48); }}
.leader-row.bronze {{ border-color:rgba(255,171,91,.46); }}
.leader-row.gold:before {{ content:""; position:absolute; left:-20%; right:-20%; top:0; height:2px; background:linear-gradient(90deg,transparent,#ffe66d,transparent); }}
.rank-badge {{ text-align:center; }}
.rank {{ font-size:30px; font-weight:950; text-shadow:0 2px 2px rgba(0,0,0,.42); }}
.crown {{ margin-top:3px; font-size:10px; color:#ffe66d; font-weight:950; letter-spacing:.8px; }}
.avatar {{ width:60px; height:60px; border-radius:50%; display:flex; align-items:center; justify-content:center; background:linear-gradient(180deg,#4b5c87,#202b4c); border:2px solid rgba(255,255,255,.20); font-size:21px; font-weight:950; color:#fff; box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 6px 14px rgba(0,0,0,.32); }}
.avatar.gold {{ border-color:rgba(255,230,109,.70); box-shadow:0 0 18px rgba(255,215,80,.20), inset 0 1px 0 rgba(255,255,255,.22),0 6px 14px rgba(0,0,0,.32); }}
.avatar.silver {{ border-color:rgba(224,232,255,.55); }}
.avatar.bronze {{ border-color:rgba(255,171,91,.55); }}
.name {{ font-size:25px; font-weight:950; color:#fff; line-height:1.05; text-shadow:0 2px 2px rgba(0,0,0,.38); }}
.sub {{ font-size:13px; color:rgba(255,255,255,.62); margin-top:3px; }}
.bar {{ width:100%; height:12px; background:rgba(7,12,32,.84); border-radius:999px; overflow:hidden; margin-top:8px; box-shadow:inset 0 2px 4px rgba(0,0,0,.48); }}
.fill {{ height:100%; background:linear-gradient(90deg,#58d8ff,#9a86ff,#ffe66d); border-radius:999px; box-shadow:0 0 12px rgba(88,216,255,.20); }}
.fill.gold {{ background:linear-gradient(90deg,#ffb84d,#ffe66d,#fff1a8); box-shadow:0 0 15px rgba(255,230,109,.32); }}
.fill.silver {{ background:linear-gradient(90deg,#b8c7ff,#f4f7ff,#9db2ff); }}
.fill.bronze {{ background:linear-gradient(90deg,#d18444,#ffbd73,#ffd2a3); }}
.coins {{ text-align:right; font-size:17px; color:rgba(255,255,255,.78); }}
.coins strong {{ display:block; font-size:30px; color:#fff; line-height:1; text-shadow:0 2px 2px rgba(0,0,0,.38); }}
.coins span,.coins small {{ display:block; }}
.coins small {{ font-size:13px; color:rgba(255,255,255,.58); margin-top:4px; }}
.empty {{ font-size:24px; color:rgba(255,255,255,.72); text-align:center; padding:50px 0; }}
</style></head><body><div class="shell"><div class="header"><div class="title-row"><div><div class="title">🏆 Coin Leaderboard</div><div class="subtitle">Top active coin balances</div></div><div class="hero-badge"><div class="label">Top Balance</div><div class="value">{top_balance:,}</div></div></div></div>
<div class="panel"><div class="summary"><div class="summary-card"><div class="summary-label">Players</div><div class="summary-value">{len(top_users)}</div></div><div class="summary-card"><div class="summary-label">Leader</div><div class="summary-value">{top_balance:,}</div></div><div class="summary-card"><div class="summary-label">Total</div><div class="summary-value">{total_balance:,}</div></div><div class="summary-card"><div class="summary-label">Average</div><div class="summary-value">{avg_balance:,}</div></div></div>
<div class="board">{rows_html}</div></div></div></body></html>"""

        image_path = Path(COIN_LEADERBOARD_IMAGE_PATH)
        image_path.parent.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = await browser.new_page(viewport={"width": 1000, "height": 1250}, device_scale_factor=1)
                await page.set_content(html_doc, wait_until="domcontentloaded")
                await page.wait_for_timeout(500)
                await page.locator(".shell").screenshot(path=str(image_path))
            finally:
                await browser.close()

        return discord.File(str(image_path), filename="coin_leaderboard.png")


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

