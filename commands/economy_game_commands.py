from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands


DAILY_COOLDOWN = 20 * 60 * 60
FARM_COOLDOWN = 45 * 60
RAID_COOLDOWN = 90 * 60
TRAIN_COOLDOWN = 4 * 60 * 60
CHEST_COST = 350
TH_BASE_COST = 500


def _now() -> int:
    return int(time.time())


def _fmt_remaining(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _title_for_th(th: int) -> str:
    if th >= 16:
        return "Legend Chief"
    if th >= 14:
        return "War General"
    if th >= 12:
        return "Clan Champion"
    if th >= 10:
        return "Siege Specialist"
    if th >= 8:
        return "Dark Elixir Raider"
    if th >= 6:
        return "Builder Base Menace"
    if th >= 4:
        return "Village Grinder"
    return "Fresh Chief"


def register_economy_game_commands(bot, ctx):
    load_coins = ctx.load_coins
    safe_load_json = ctx.safe_load_json
    safe_save_json = ctx.safe_save_json
    LINKED_FILE = ctx.LINKED_FILE
    normalize_linked_data = ctx.normalize_linked_data
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    get_inventory_text = ctx.get_inventory_text
    SHOP_ITEMS = ctx.SHOP_ITEMS
    economy = getattr(ctx, "economy", None)

    async def _ensure_user(user: discord.abc.User, display_name: str | None = None):
        user_id = str(user.id)
        name = display_name or getattr(user, "display_name", None) or getattr(user, "name", "Unknown")
        result = {}

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})
            entry = users.setdefault(user_id, {"balance": 0, "lifetime_earned": 0, "name": name})
            entry.setdefault("balance", 0)
            entry.setdefault("lifetime_earned", 0)
            entry.setdefault("gems", 0)
            entry.setdefault("raid_medals", 0)
            entry.setdefault("clan_xp", 0)
            entry.setdefault("town_hall", 1)
            entry.setdefault("daily_streak", 0)
            entry.setdefault("cooldowns", {})
            entry.setdefault("stats", {"farm_runs": 0, "raids": 0, "raid_wins": 0, "chests_opened": 0})
            entry["name"] = name
            result.update(entry)
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        return result

    async def _grant(user, *, gold=0, gems=0, medals=0, clan_xp=0, name=None, stat_updates=None):
        user_id = str(user.id)
        display = name or getattr(user, "display_name", None) or getattr(user, "name", "Unknown")
        result = {}

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})
            entry = users.setdefault(user_id, {"balance": 0, "lifetime_earned": 0, "name": display})
            entry["balance"] = int(entry.get("balance", 0) or 0) + int(gold)
            entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + max(0, int(gold))
            entry["gems"] = int(entry.get("gems", 0) or 0) + int(gems)
            entry["raid_medals"] = int(entry.get("raid_medals", 0) or 0) + int(medals)
            entry["clan_xp"] = int(entry.get("clan_xp", 0) or 0) + int(clan_xp)
            entry.setdefault("town_hall", 1)
            entry.setdefault("cooldowns", {})
            stats = entry.setdefault("stats", {})
            for key, delta in (stat_updates or {}).items():
                stats[key] = int(stats.get(key, 0) or 0) + int(delta)
            entry["name"] = display
            result.update(entry)
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        return result

    async def _cooldown_check(user_id: str, key: str, cooldown_seconds: int):
        stored = await load_coins()
        entry = stored.get("users", {}).get(str(user_id), {})
        cooldowns = entry.get("cooldowns", {}) if isinstance(entry, dict) else {}
        last = int(cooldowns.get(key, 0) or 0)
        remaining = cooldown_seconds - (_now() - last)
        return max(0, remaining)

    async def _stamp_cooldown(user_id: str, key: str):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {"balance": 0, "lifetime_earned": 0, "name": "Unknown"})
            cooldowns = entry.setdefault("cooldowns", {})
            cooldowns[key] = _now()
            return stored
        await ctx.update_json_file(ctx.COINS_FILE, _update)

    async def _linked_accounts_text(user_id: str) -> str:
        linked_raw = await safe_load_json(LINKED_FILE)
        linked = normalize_linked_data(linked_raw)
        entries = linked.get(str(user_id), [])
        if not entries:
            return "No Clash account linked yet. Use `/link` for full clan reward tracking."
        return ", ".join(f"{e.get('name', 'Unknown')} ({e.get('tag', 'Unknown')})" for e in entries)

    @bot.tree.command(name="daily", description="Claim your daily Clash economy loot")
    async def daily(interaction: discord.Interaction):
        await _ensure_user(interaction.user, getattr(interaction.user, "display_name", None))
        remaining = await _cooldown_check(str(interaction.user.id), "daily", DAILY_COOLDOWN)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Your collectors are still refilling. Try again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return

        stored = await load_coins()
        entry = stored.get("users", {}).get(str(interaction.user.id), {})
        old_streak = int(entry.get("daily_streak", 0) or 0)
        last_daily = int(entry.get("cooldowns", {}).get("daily", 0) or 0)
        streak = old_streak + 1 if last_daily and (_now() - last_daily) <= 48 * 60 * 60 else 1
        base_gold = random.randint(225, 450)
        streak_bonus = min(750, streak * 35)
        gems = 1 if random.random() < 0.30 else 0
        clan_xp = random.randint(8, 18)

        def _update(data):
            if not isinstance(data, dict):
                data = {}
            users = data.setdefault("users", {})
            user_entry = users.setdefault(str(interaction.user.id), {"balance": 0, "lifetime_earned": 0, "name": interaction.user.display_name})
            user_entry["balance"] = int(user_entry.get("balance", 0) or 0) + base_gold + streak_bonus
            user_entry["lifetime_earned"] = int(user_entry.get("lifetime_earned", 0) or 0) + base_gold + streak_bonus
            user_entry["gems"] = int(user_entry.get("gems", 0) or 0) + gems
            user_entry["clan_xp"] = int(user_entry.get("clan_xp", 0) or 0) + clan_xp
            user_entry["daily_streak"] = streak
            user_entry.setdefault("town_hall", 1)
            user_entry["name"] = interaction.user.display_name
            user_entry.setdefault("cooldowns", {})["daily"] = _now()
            return data

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        embed = discord.Embed(title="🏰 Daily Village Loot", color=0xF1C40F)
        embed.description = f"You collected your mines, pumps, and clan cart.\n\n**+{base_gold + streak_bonus:,} Gold**\n**+{gems} Gems**\n**+{clan_xp} Clan XP**"
        embed.add_field(name="Streak", value=f"{streak} day(s) (+{streak_bonus:,} Gold bonus)", inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="farm", description="Farm a dead base for gold, gems, and clan XP")
    async def farm(interaction: discord.Interaction):
        await _ensure_user(interaction.user, interaction.user.display_name)
        remaining = await _cooldown_check(str(interaction.user.id), "farm", FARM_COOLDOWN)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Your army is still training. Try `/farm` again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        gold = random.randint(120, 330)
        gems = 1 if random.random() < 0.12 else 0
        xp = random.randint(4, 11)
        scenarios = [
            "You found a dead base with full collectors.",
            "You sniped exposed storages before the defender logged in.",
            "Your sneaky goblins emptied the outside collectors.",
            "You farmed a rushed base and dipped before the Eagle woke up.",
        ]
        await _grant(interaction.user, gold=gold, gems=gems, clan_xp=xp, stat_updates={"farm_runs": 1})
        await _stamp_cooldown(str(interaction.user.id), "farm")
        await interaction.response.send_message(f"🌾 **Farm Run Complete**\n{random.choice(scenarios)}\n\n+**{gold:,} Gold** | +**{gems} Gems** | +**{xp} Clan XP**")

    @bot.tree.command(name="raid", description="Attack a base for a higher-risk Clash economy reward")
    async def raid(interaction: discord.Interaction):
        await _ensure_user(interaction.user, interaction.user.display_name)
        remaining = await _cooldown_check(str(interaction.user.id), "raid", RAID_COOLDOWN)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Your war army is not ready. Try `/raid` again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        entry = (await load_coins()).get("users", {}).get(str(interaction.user.id), {})
        th = int(entry.get("town_hall", 1) or 1)
        roll = random.random()
        if roll < 0.12:
            loss = min(int(entry.get("balance", 0) or 0), random.randint(50, 180))
            await _grant(interaction.user, gold=-loss, clan_xp=3, stat_updates={"raids": 1})
            result = f"💀 **Raid Failed**\nThe base had a maxed Monolith and your army got cooked.\n\n-**{loss:,} Gold** | +**3 Clan XP**"
        elif roll < 0.42:
            gold = random.randint(180, 420) + th * 20
            xp = random.randint(8, 16)
            await _grant(interaction.user, gold=gold, clan_xp=xp, stat_updates={"raids": 1})
            result = f"⭐ **One-Star Raid**\nYou grabbed the Town Hall and escaped with loot.\n\n+**{gold:,} Gold** | +**{xp} Clan XP**"
        elif roll < 0.82:
            gold = random.randint(350, 700) + th * 35
            medals = 1 if random.random() < 0.35 else 0
            xp = random.randint(15, 28)
            await _grant(interaction.user, gold=gold, medals=medals, clan_xp=xp, stat_updates={"raids": 1, "raid_wins": 1})
            result = f"⭐⭐ **Two-Star Raid**\nSolid hit. Storages cracked, heroes survived.\n\n+**{gold:,} Gold** | +**{medals} Raid Medals** | +**{xp} Clan XP**"
        else:
            gold = random.randint(725, 1150) + th * 50
            gems = 1 if random.random() < 0.35 else 0
            medals = random.randint(1, 3)
            xp = random.randint(30, 55)
            await _grant(interaction.user, gold=gold, gems=gems, medals=medals, clan_xp=xp, stat_updates={"raids": 1, "raid_wins": 1, "triples": 1})
            result = f"⭐⭐⭐ **Triple!**\nYou crushed the base and brought the loot cart home.\n\n+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**"
        await _stamp_cooldown(str(interaction.user.id), "raid")
        await interaction.response.send_message(result)

    @bot.tree.command(name="train", description="Train your army for a small XP reward and future progression")
    async def train(interaction: discord.Interaction):
        await _ensure_user(interaction.user, interaction.user.display_name)
        remaining = await _cooldown_check(str(interaction.user.id), "train", TRAIN_COOLDOWN)
        if remaining > 0:
            await interaction.response.send_message(f"⏳ Your troops are already training. Try again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        xp = random.randint(18, 35)
        await _grant(interaction.user, clan_xp=xp, stat_updates={"training_sessions": 1})
        await _stamp_cooldown(str(interaction.user.id), "train")
        await interaction.response.send_message(f"🧪 **Army Trained**\nYou practiced funneling, spell timing, and cleanup pathing.\n\n+**{xp} Clan XP**")

    @bot.tree.command(name="openchest", description="Buy and open a Clash-style war chest")
    async def openchest(interaction: discord.Interaction):
        spend = await spend_coins(str(interaction.user.id), CHEST_COST)
        if not spend.get("ok"):
            await interaction.response.send_message(f"❌ You need **{CHEST_COST:,} Gold** to open a War Chest.", ephemeral=True)
            return
        roll = random.random()
        awarded_item = None
        if roll < 0.10:
            gold, gems, medals, xp = random.randint(900, 1500), random.randint(2, 5), random.randint(2, 5), random.randint(30, 60)
            rarity = "Legendary War Chest"
        elif roll < 0.35:
            gold, gems, medals, xp = random.randint(450, 850), random.randint(1, 3), random.randint(1, 3), random.randint(18, 35)
            rarity = "Epic War Chest"
        else:
            gold, gems, medals, xp = random.randint(150, 425), 0 if random.random() < 0.65 else 1, random.randint(0, 1), random.randint(8, 18)
            rarity = "Common War Chest"
        if random.random() < 0.22 and SHOP_ITEMS:
            awarded_item = random.choice(list(SHOP_ITEMS.keys()))
            await add_shop_item(str(interaction.user.id), awarded_item, 1)
        await _grant(interaction.user, gold=gold, gems=gems, medals=medals, clan_xp=xp, stat_updates={"chests_opened": 1})
        item_text = f"\n🎒 Bonus item: **{SHOP_ITEMS[awarded_item]['name']}**" if awarded_item else ""
        await interaction.response.send_message(f"📦 **{rarity} Opened**\nCost: **{CHEST_COST:,} Gold**\n\n+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**{item_text}")

    @bot.tree.command(name="upgradehall", description="Upgrade your Discord economy Town Hall")
    async def upgradehall(interaction: discord.Interaction):
        await _ensure_user(interaction.user, interaction.user.display_name)
        stored = await load_coins()
        entry = stored.get("users", {}).get(str(interaction.user.id), {})
        th = int(entry.get("town_hall", 1) or 1)
        if th >= 16:
            await interaction.response.send_message("🏰 Your economy Town Hall is already maxed at TH16.", ephemeral=True)
            return
        cost = TH_BASE_COST * th
        xp_required = th * 100
        if int(entry.get("clan_xp", 0) or 0) < xp_required:
            await interaction.response.send_message(f"❌ You need **{xp_required:,} Clan XP** to upgrade to TH{th + 1}. You currently have **{int(entry.get('clan_xp', 0) or 0):,}**.", ephemeral=True)
            return
        spend = await spend_coins(str(interaction.user.id), cost)
        if not spend.get("ok"):
            await interaction.response.send_message(f"❌ You need **{cost:,} Gold** to upgrade to TH{th + 1}.", ephemeral=True)
            return

        def _update(data):
            users = data.setdefault("users", {})
            user_entry = users.setdefault(str(interaction.user.id), {})
            user_entry["town_hall"] = th + 1
            return data
        await ctx.update_json_file(ctx.COINS_FILE, _update)
        await interaction.response.send_message(f"🏰 **Town Hall Upgraded!**\nYou are now **TH{th + 1}** — title unlocked: **{_title_for_th(th + 1)}**")

    @bot.tree.command(name="village", description="View your or another member's Clash economy profile")
    @app_commands.describe(member="Optional member to view")
    async def village(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        await _ensure_user(target, getattr(target, "display_name", None))
        stored = await load_coins()
        data = stored.get("users", {}).get(str(target.id), {})
        stats = data.get("stats", {}) if isinstance(data, dict) else {}
        th = int(data.get("town_hall", 1) or 1)
        embed = discord.Embed(title=f"🏰 {target.display_name}'s Village", color=0x3498DB)
        embed.add_field(name="Town Hall", value=f"TH{th}", inline=True)
        embed.add_field(name="Title", value=_title_for_th(th), inline=True)
        embed.add_field(name="Gold", value=f"{int(data.get('balance', 0) or 0):,}", inline=True)
        embed.add_field(name="Gems", value=f"{int(data.get('gems', 0) or 0):,}", inline=True)
        embed.add_field(name="Raid Medals", value=f"{int(data.get('raid_medals', 0) or 0):,}", inline=True)
        embed.add_field(name="Clan XP", value=f"{int(data.get('clan_xp', 0) or 0):,}", inline=True)
        embed.add_field(name="Daily Streak", value=f"{int(data.get('daily_streak', 0) or 0)} day(s)", inline=True)
        embed.add_field(name="Raid Record", value=f"{int(stats.get('raid_wins', 0) or 0)} wins / {int(stats.get('raids', 0) or 0)} raids", inline=True)
        embed.add_field(name="Linked Accounts", value=await _linked_accounts_text(str(target.id)), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="economyhelp", description="Show the expanded Clash economy command loop")
    async def economyhelp(interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ Clash Economy Commands", color=0x9B59B6)
        embed.description = "Build your mini village inside Discord: collect, farm, raid, open chests, upgrade, and flex the leaderboard."
        embed.add_field(name="Earn", value="`/daily` `/farm` `/raid` `/train`", inline=False)
        embed.add_field(name="Spend", value="`/shop` `/buy` `/useitem` `/openchest` `/upgradehall`", inline=False)
        embed.add_field(name="Flex", value="`/village` `/balance` `/inventory` `/coinleaderboard`", inline=False)
        embed.add_field(name="Chaos", value="`/steal` is still available, with shields and cooldowns.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
