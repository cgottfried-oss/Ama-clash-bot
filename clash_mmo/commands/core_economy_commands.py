from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands


DAILY_COOLDOWN = 20 * 60 * 60
FARM_COOLDOWN = 3 * 60
RAID_COOLDOWN = 10 * 60
TRAIN_COOLDOWN = 5 * 60
TH_BASE_COST = 500

RAID_CHEST_REWARDS = {
    1: "common_chest",
    2: "rare_chest",
    3: "epic_chest",
}

CHEST_NAMES = {
    "common_chest": "Common War Chest",
    "rare_chest": "Rare War Chest",
    "epic_chest": "Epic War Chest",
    "legend_chest": "Legend Chest",
}

TH_UNLOCKS = {
    "farm": 1,
    "train": 1,
    "raid": 3,
    "openchest": 5,
    "legend_chest": 7,
    "dark_elixir": 9,
    "admin_view": 1,
}

ACHIEVEMENTS = {
    "first_daily": {"name": "First Collector Run", "reward": 75, "desc": "Claim /daily once."},
    "first_farm": {"name": "Dead Base Hunter", "reward": 100, "desc": "Complete your first /farm."},
    "first_raid": {"name": "First War Attack", "reward": 150, "desc": "Complete your first /raid."},
    "first_triple": {"name": "Triple Threat", "reward": 350, "desc": "Hit your first 3-star raid."},
    "streak_7": {"name": "One Week Grinder", "reward": 500, "desc": "Reach a 7-day daily streak."},
    "ten_chests": {"name": "Chest Addict", "reward": 650, "desc": "Open 10 chests."},
    "th10": {"name": "Siege Machine Ready", "reward": 1000, "desc": "Reach economy TH10."},
    "rich_10k": {"name": "Clan Treasury", "reward": 750, "desc": "Hold 10,000 Gold."},
}


def _now() -> int:
    return int(time.time())
    
def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def register_core_economy_commands(bot, ctx):
    load_coins = ctx.load_coins
    safe_load_json = ctx.safe_load_json
    safe_save_json = ctx.safe_save_json
    LINKED_FILE = ctx.LINKED_FILE
    normalize_linked_data = ctx.normalize_linked_data
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    get_inventory_text = ctx.get_inventory_text
    consume_shop_item = ctx.consume_shop_item
    SHOP_ITEMS = ctx.SHOP_ITEMS
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID

    def _is_admin(member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in member.roles)
        
    @bot.tree.command(name="adminview", description="Leader tool: privately view a member's economy account and inventory")
    @app_commands.describe(member="Member to inspect")
    async def adminview(interaction: discord.Interaction, member: discord.Member):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return

        await _ensure_user(member, member.display_name)

        stored = await load_coins()
        user_entry = stored.get("users", {}).get(str(member.id), {})

        shop_data = await ctx.load_shop_data()
        inventory = (
            shop_data.get("users", {})
            .get(str(member.id), {})
            .get("inventory", {})
        )

        cooldowns = user_entry.get("cooldowns", {}) if isinstance(user_entry.get("cooldowns", {}), dict) else {}
        boosts = user_entry.get("boosts", {}) if isinstance(user_entry.get("boosts", {}), dict) else {}
        stats = user_entry.get("stats", {}) if isinstance(user_entry.get("stats", {}), dict) else {}

        inventory_lines = []
        for item_key, qty in sorted(inventory.items()):
            item_name = SHOP_ITEMS.get(item_key, {}).get("name", item_key)
            inventory_lines.append(f"**{item_name}** (`{item_key}`): x{int(qty or 0)}")

        if not inventory_lines:
            inventory_lines = ["No inventory items."]

        cooldown_lines = []
        for key, value in sorted(cooldowns.items()):
            try:
                timestamp = int(value or 0)
                cooldown_lines.append(f"`{key}`: {discord.utils.format_dt(datetime.fromtimestamp(timestamp), style='R')}")
            except Exception:
                cooldown_lines.append(f"`{key}`: {value}")

        if not cooldown_lines:
            cooldown_lines = ["No cooldowns recorded."]

        boost_lines = [
            f"`{key}`: {int(value or 0)} charge(s)"
            for key, value in sorted(boosts.items())
        ] or ["No active boost charges."]

        stat_lines = [
            f"`{key}`: {value}"
            for key, value in sorted(stats.items())
        ] or ["No stats recorded."]

        embed = discord.Embed(
            title=f"🛠️ Admin Economy View: {member.display_name}",
            color=0xE67E22,
        )

        embed.add_field(
            name="Account",
            value=(
                f"Gold: **{int(user_entry.get('balance', 0) or 0):,}**\n"
                f"Lifetime Earned: **{int(user_entry.get('lifetime_earned', 0) or 0):,}**\n"
                f"Clan XP: **{int(user_entry.get('clan_xp', 0) or 0):,}**\n"
                f"Town Hall: **{int(user_entry.get('town_hall', 1) or 1)}**\n"
                f"Gems: **{int(user_entry.get('gems', 0) or 0):,}**\n"
                f"Raid Medals: **{int(user_entry.get('raid_medals', 0) or 0):,}**\n"
                f"Dark Elixir: **{int(user_entry.get('dark_elixir', 0) or 0):,}**"
            ),
            inline=False,
        )

        embed.add_field(name="Inventory", value="\n".join(inventory_lines[:20]), inline=False)
        embed.add_field(name="Boosts", value="\n".join(boost_lines[:10]), inline=False)
        embed.add_field(name="Cooldowns", value="\n".join(cooldown_lines[:10]), inline=False)
        embed.add_field(name="Stats", value="\n".join(stat_lines[:15]), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @bot.tree.command(name="adminset", description="Leader tool: set a member's economy account values")
    @app_commands.describe(
        member="Member to adjust",
        gold="Set current Gold balance",
        clan_xp="Set Clan XP",
        gems="Set Gems",
        medals="Set Raid Medals",
        dark_elixir="Set Dark Elixir",
        town_hall="Set Town Hall level",
        reason="Reason for this adjustment",
    )
    async def adminset(
        interaction: discord.Interaction,
        member: discord.Member,
        gold: int | None = None,
        clan_xp: int | None = None,
        gems: int | None = None,
        medals: int | None = None,
        dark_elixir: int | None = None,
        town_hall: int | None = None,
        reason: str = "Manual admin adjustment",
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return

        user_id = str(member.id)
        name = getattr(member, "display_name", member.name)

        changes = []

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}

            users = stored.setdefault("users", {})
            entry = users.setdefault(user_id, {
                "balance": 0,
                "lifetime_earned": 0,
                "name": name,
            })

            entry.setdefault("gems", 0)
            entry.setdefault("raid_medals", 0)
            entry.setdefault("clan_xp", 0)
            entry.setdefault("town_hall", 1)
            entry.setdefault("dark_elixir", 0)
            entry.setdefault("cooldowns", {})
            entry.setdefault("boosts", {})
            entry.setdefault("achievements", [])
            entry.setdefault("stats", {})

            if gold is not None:
                entry["balance"] = max(0, int(gold))
                changes.append(f"Gold → **{entry['balance']:,}**")

            if clan_xp is not None:
                entry["clan_xp"] = max(0, int(clan_xp))
                changes.append(f"Clan XP → **{entry['clan_xp']:,}**")

            if gems is not None:
                entry["gems"] = max(0, int(gems))
                changes.append(f"Gems → **{entry['gems']:,}**")

            if medals is not None:
                entry["raid_medals"] = max(0, int(medals))
                changes.append(f"Raid Medals → **{entry['raid_medals']:,}**")

            if dark_elixir is not None:
                entry["dark_elixir"] = max(0, int(dark_elixir))
                changes.append(f"Dark Elixir → **{entry['dark_elixir']:,}**")

            if town_hall is not None:
                entry["town_hall"] = max(1, min(16, int(town_hall)))
                changes.append(f"Town Hall → **TH{entry['town_hall']}**")

            entry["name"] = name
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)

        if not changes:
            await interaction.response.send_message(
                "ℹ️ No values were changed. Add at least one field like `gold`, `clan_xp`, or `town_hall`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Updated economy account for {member.mention}\n"
            + "\n".join(changes)
            + f"\nReason: {reason}",
            ephemeral=True,
        )
        
    @bot.tree.command(name="adminclearinventory", description="Leader tool: clear a member's shop inventory")
    @app_commands.describe(
        member="Member whose inventory should be cleared",
        reason="Reason for clearing inventory",
    )
    async def adminclearinventory(
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "Manual inventory rollback",
    ):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return

        user_id = str(member.id)

        def _update_shop(data):
            if not isinstance(data, dict):
                data = {}
            users = data.setdefault("users", {})
            entry = users.setdefault(user_id, {})
            entry["inventory"] = {}
            return data

        await ctx.update_json_file(ctx.SHOP_FILE, _update_shop)

        await interaction.response.send_message(
            f"🧹 Cleared inventory for {member.mention}.\nReason: {reason}",
            ephemeral=True,
        )

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
            entry.setdefault("dark_elixir", 0)
            entry.setdefault("cooldowns", {})
            entry.setdefault("boosts", {})
            entry.setdefault("achievements", [])
            entry.setdefault("stats", {"farm_runs": 0, "raids": 0, "raid_wins": 0, "chests_opened": 0})
            entry["name"] = name
            result.update(entry)
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        return result

    async def _award_achievements(user, entry: dict):
        user_id = str(user.id)
        current = set(entry.get("achievements", []) or [])
        stats = entry.get("stats", {}) if isinstance(entry.get("stats", {}), dict) else {}
        unlocked = []
        checks = {
            "first_daily": int(entry.get("daily_streak", 0) or 0) >= 1,
            "first_farm": int(stats.get("farm_runs", 0) or 0) >= 1,
            "first_raid": int(stats.get("raids", 0) or 0) >= 1,
            "first_triple": int(stats.get("triples", 0) or 0) >= 1,
            "streak_7": int(entry.get("daily_streak", 0) or 0) >= 7,
            "ten_chests": int(stats.get("chests_opened", 0) or 0) >= 10,
            "th10": int(entry.get("town_hall", 1) or 1) >= 10,
            "rich_10k": int(entry.get("balance", 0) or 0) >= 10000,
        }
        for key, passed in checks.items():
            if passed and key not in current:
                unlocked.append(key)
        if not unlocked:
            return []

        total_reward = sum(int(ACHIEVEMENTS[k]["reward"]) for k in unlocked)

        def _update(stored):
            users = stored.setdefault("users", {})
            e = users.setdefault(user_id, {})
            achievements = set(e.get("achievements", []) or [])
            for key in unlocked:
                achievements.add(key)
            e["achievements"] = sorted(achievements)
            e["balance"] = int(e.get("balance", 0) or 0) + total_reward
            e["lifetime_earned"] = int(e.get("lifetime_earned", 0) or 0) + total_reward
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        return unlocked

    async def _post_achievement_followup(interaction, unlocked: list[str]):
        if not unlocked:
            return
        lines = [f"🏆 **{ACHIEVEMENTS[k]['name']}** — +{ACHIEVEMENTS[k]['reward']:,} Gold" for k in unlocked]
        await interaction.followup.send("**Achievement Unlocked!**\n" + "\n".join(lines), ephemeral=False)

    async def _grant(user, *, gold=0, gems=0, medals=0, clan_xp=0, dark_elixir=0, name=None, stat_updates=None):
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
            entry["balance"] = max(0, int(entry.get("balance", 0) or 0) + int(gold))
            entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + max(0, int(gold))
            entry["gems"] = max(0, int(entry.get("gems", 0) or 0) + int(gems))
            entry["raid_medals"] = max(0, int(entry.get("raid_medals", 0) or 0) + int(medals))
            entry["clan_xp"] = max(0, int(entry.get("clan_xp", 0) or 0) + int(clan_xp))
            entry["dark_elixir"] = max(0, int(entry.get("dark_elixir", 0) or 0) + int(dark_elixir))
            entry.setdefault("town_hall", 1)
            entry.setdefault("cooldowns", {})
            entry.setdefault("boosts", {})
            entry.setdefault("achievements", [])
            stats = entry.setdefault("stats", {})
            for key, delta in (stat_updates or {}).items():
                stats[key] = int(stats.get(key, 0) or 0) + int(delta)
            entry["name"] = display
            result.update(entry)
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        stored = await load_coins()
        entry = stored.get("users", {}).get(user_id, {})
        await _award_achievements(user, entry)
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

    async def _consume_boost_charge(user_id: str, boost_key: str):
        result = {"active": False, "charges_left": 0}
        def _update(stored):
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {})
            boosts = entry.setdefault("boosts", {})
            charges = int(boosts.get(boost_key, 0) or 0)
            if charges > 0:
                charges -= 1
                result["active"] = True
                result["charges_left"] = charges
                if charges <= 0:
                    boosts.pop(boost_key, None)
                else:
                    boosts[boost_key] = charges
            return stored
        await ctx.update_json_file(ctx.COINS_FILE, _update)
        return result

    async def _add_boost_charges(user_id: str, boost_key: str, charges: int):
        BOOST_CHARGE_CAPS = {
            "training_potion": 6,
            "resource_potion": 8,
        }
    
        def _update(stored):
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {})
            boosts = entry.setdefault("boosts", {})
    
            current = int(boosts.get(boost_key, 0) or 0)
            cap = BOOST_CHARGE_CAPS.get(boost_key)
    
            if cap is not None:
                boosts[boost_key] = min(cap, current + int(charges))
            else:
                boosts[boost_key] = current + int(charges)
    
            return stored
    
        await ctx.update_json_file(ctx.COINS_FILE, _update)

    async def _clear_cooldowns(user_id: str, keys: list[str]):
        def _update(stored):
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {})
            cooldowns = entry.setdefault("cooldowns", {})
            for key in keys:
                cooldowns.pop(key, None)
            return stored
        await ctx.update_json_file(ctx.COINS_FILE, _update)
        
    async def _daily_counter_check(user_id: str, key: str, daily_limit: int):
        stored = await load_coins()
        entry = stored.get("users", {}).get(str(user_id), {})
        counters = entry.get("daily_counters", {}) if isinstance(entry, dict) else {}
        day = counters.get(_day_key(), {}) if isinstance(counters, dict) else {}
        used = int(day.get(key, 0) or 0)
        remaining = max(0, int(daily_limit) - used)
        return used, remaining

    async def _increment_daily_counter(user_id: str, key: str, amount: int = 1):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {})
            counters = entry.setdefault("daily_counters", {})
            today = counters.setdefault(_day_key(), {})
            today[key] = int(today.get(key, 0) or 0) + int(amount)
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)

    def _th_locked_message(command: str, required: int) -> str:
        return f"🔒 `{command}` unlocks at **Town Hall {required}**. Use `/daily`, `/farm`, `/train`, and `/upgradehall` to progress."

    @bot.tree.command(name="daily", description="Claim your daily Clash economy loot")
    async def daily(interaction: discord.Interaction):
        await interaction.response.defer()
        await _ensure_user(interaction.user, getattr(interaction.user, "display_name", None))
        remaining = await _cooldown_check(str(interaction.user.id), "daily", DAILY_COOLDOWN)
        if remaining > 0:
            await interaction.followup.send(f"⏳ Your collectors are still refilling. Try again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
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
            user_entry.setdefault("achievements", [])
            user_entry["name"] = interaction.user.display_name
            user_entry.setdefault("cooldowns", {})["daily"] = _now()
            return data

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        stored = await load_coins()
        unlocked = await _award_achievements(interaction.user, stored.get("users", {}).get(str(interaction.user.id), {}))
        embed = discord.Embed(title="🏰 Daily Village Loot", color=0xF1C40F)
        embed.description = f"You collected your mines, pumps, and clan cart.\n\n**+{base_gold + streak_bonus:,} Gold**\n**+{gems} Gems**\n**+{clan_xp} Clan XP**"
        embed.add_field(name="Streak", value=f"{streak} day(s) (+{streak_bonus:,} Gold bonus)", inline=False)
        await interaction.followup.send(embed=embed)
        await _post_achievement_followup(interaction, unlocked)

    @bot.tree.command(name="farm", description="Farm a dead base for gold, gems, and clan XP")
    async def farm(interaction: discord.Interaction):
        await interaction.response.defer()
        entry = await _ensure_user(interaction.user, interaction.user.display_name)
        remaining = await _cooldown_check(str(interaction.user.id), "farm", FARM_COOLDOWN)
        if remaining > 0:
            await interaction.followup.send(f"⏳ Your army is still training. Try `/farm` again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        gold = random.randint(120, 330)
        gems = 1 if random.random() < 0.12 else 0
        xp = random.randint(4, 11)
        boost = await _consume_boost_charge(str(interaction.user.id), "resource_potion")
        boost_note = ""
        if boost["active"]:
            gold = int(round(gold * 1.35))
            boost_note = f"\n🧪 Resource Potion boosted this run. Charges left: **{boost['charges_left']}**"
        scenarios = [
            "You found a dead base with full collectors.",
            "You sniped exposed storages before the defender logged in.",
            "Your sneaky goblins emptied the outside collectors.",
            "You farmed a rushed base and dipped before the Eagle woke up.",
        ]
        await _grant(interaction.user, gold=gold, gems=gems, clan_xp=xp, stat_updates={"farm_runs": 1})
        await _stamp_cooldown(str(interaction.user.id), "farm")
        stored = await load_coins()
        unlocked = await _award_achievements(interaction.user, stored.get("users", {}).get(str(interaction.user.id), {}))
        await interaction.followup.send(f"🌾 **Farm Run Complete**\n{random.choice(scenarios)}\n\n+**{gold:,} Gold** | +**{gems} Gems** | +**{xp} Clan XP**{boost_note}")
        await _post_achievement_followup(interaction, unlocked)

    @bot.tree.command(name="raid", description="Attack a base for a higher-risk Clash economy reward")
    async def raid(interaction: discord.Interaction):
        await interaction.response.defer()
        entry = await _ensure_user(interaction.user, interaction.user.display_name)
        th = int(entry.get("town_hall", 1) or 1)
        if th < TH_UNLOCKS["raid"]:
            await interaction.followup.send(_th_locked_message("/raid", TH_UNLOCKS["raid"]), ephemeral=True)
            return
        remaining = await _cooldown_check(str(interaction.user.id), "raid", RAID_COOLDOWN)
        if remaining > 0:
            await interaction.followup.send(f"⏳ Your war army is not ready. Try `/raid` again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        roll = random.random()
        stars = 0
        earned_chest = None
        boost = await _consume_boost_charge(str(interaction.user.id), "training_potion")
        boost_note = ""
        gold_multiplier = 1.25 if boost["active"] else 1.0
        xp_multiplier = 1.25 if boost["active"] else 1.0
        if boost["active"]:
            boost_note = f"\n🧪 Training Potion boosted this raid. Charges left: **{boost['charges_left']}**"
        if roll < 0.12:
            loss = min(int(entry.get("balance", 0) or 0), random.randint(50, 180))
            await _grant(interaction.user, gold=-loss, clan_xp=3, stat_updates={"raids": 1})
            result = f"💀 **Raid Failed**\nThe base had a maxed Monolith and your army got cooked.\n\n-**{loss:,} Gold** | +**3 Clan XP**"
        elif roll < 0.42:
            gold = int(round((random.randint(180, 420) + th * 20) * gold_multiplier))
            xp = int(round(random.randint(8, 16) * xp_multiplier))
            await _grant(interaction.user, gold=gold, clan_xp=xp, stat_updates={"raids": 1})
            stars = 1
            earned_chest = RAID_CHEST_REWARDS[1]
            await add_shop_item(str(interaction.user.id), earned_chest, 1)
            result = f"⭐ **One-Star Raid**\nYou grabbed the Town Hall and escaped with loot.\n\n+**{gold:,} Gold** | +**{xp} Clan XP**{boost_note}"
        elif roll < 0.82:
            gold = int(round((random.randint(350, 700) + th * 35) * gold_multiplier))
            medals = 1 if random.random() < 0.35 else 0
            xp = int(round(random.randint(15, 28) * xp_multiplier))
            await _grant(interaction.user, gold=gold, medals=medals, clan_xp=xp, stat_updates={"raids": 1, "raid_wins": 1})
            stars = 2
            earned_chest = RAID_CHEST_REWARDS[2]
            await add_shop_item(str(interaction.user.id), earned_chest, 1)
            result = f"⭐⭐ **Two-Star Raid**\nSolid hit. Storages cracked, heroes survived.\n📦 Chest earned: **{CHEST_NAMES[earned_chest]}**\n\n+**{gold:,} Gold** | +**{medals} Raid Medals** | +**{xp} Clan XP**{boost_note}"
        else:
            gold = int(round((random.randint(725, 1150) + th * 50) * gold_multiplier))
            gems = 1 if random.random() < 0.35 else 0
            medals = random.randint(1, 3)
            xp = int(round(random.randint(30, 55) * xp_multiplier))
            dark_elixir = random.randint(20, 80) if th >= TH_UNLOCKS["dark_elixir"] else 0
            await _grant(interaction.user, gold=gold, gems=gems, medals=medals, clan_xp=xp, dark_elixir=dark_elixir, stat_updates={"raids": 1, "raid_wins": 1, "triples": 1})
            stars = 3
            earned_chest = RAID_CHEST_REWARDS[3]
            await add_shop_item(str(interaction.user.id), earned_chest, 1)
            de_text = f" | +**{dark_elixir} Dark Elixir**" if dark_elixir else ""
            result = f"⭐⭐⭐ **Triple!**\nYou crushed the base and brought the loot cart home.\n📦 Chest earned: **{CHEST_NAMES[earned_chest]}**\n\n+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**{de_text}{boost_note}"
        await _stamp_cooldown(str(interaction.user.id), "raid")
        stored = await load_coins()
        unlocked = await _award_achievements(interaction.user, stored.get("users", {}).get(str(interaction.user.id), {}))
        await interaction.followup.send(result)
        await _post_achievement_followup(interaction, unlocked)

    @bot.tree.command(name="train", description="Train your army for a small XP reward and future progression")
    async def train(interaction: discord.Interaction):
        await interaction.response.defer()
        await _ensure_user(interaction.user, interaction.user.display_name)
        remaining = await _cooldown_check(str(interaction.user.id), "train", TRAIN_COOLDOWN)
        if remaining > 0:
            await interaction.followup.send(f"⏳ Your troops are already training. Try again in **{_fmt_remaining(remaining)}**.", ephemeral=True)
            return
        xp = random.randint(18, 35)
        await _grant(interaction.user, clan_xp=xp, stat_updates={"training_sessions": 1})
        await _stamp_cooldown(str(interaction.user.id), "train")
        await interaction.followup.send(f"🧪 **Army Trained**\nYou practiced funneling, spell timing, and cleanup pathing.\n\n+**{xp} Clan XP**")

    @bot.tree.command(name="openchest", description="Open a chest earned from raids or boss events")
    @app_commands.describe(chest="Chest type to open")
    @app_commands.choices(chest=[
    app_commands.Choice(name="Common War Chest", value="common_chest"),
    app_commands.Choice(name="Rare War Chest", value="rare_chest"),
    app_commands.Choice(name="Epic War Chest", value="epic_chest"),
    app_commands.Choice(name="Legend Chest", value="legend_chest"),
])
async def openchest(interaction: discord.Interaction, chest: app_commands.Choice[str]):
    await interaction.response.defer()

    entry = await _ensure_user(interaction.user, interaction.user.display_name)
    th = int(entry.get("town_hall", 1) or 1)

    if th < TH_UNLOCKS["openchest"]:
        await interaction.followup.send(_th_locked_message("/openchest", TH_UNLOCKS["openchest"]), ephemeral=True)
        return

    chest_id = chest.value

    consume = await consume_shop_item(str(interaction.user.id), chest_id, 1)
    if not consume.get("ok"):
        await interaction.followup.send(
            f"❌ You do not have a **{CHEST_NAMES.get(chest_id, chest_id)}** to open.\n"
            "Earn chests from raids: 1⭐ = Common, 2⭐ = Rare, 3⭐ = Epic. Legend Chests drop from boss events.",
            ephemeral=True,
        )
        return

    roll = random.random()
    awarded_item = None

    if chest_id == "legend_chest":
        gold = random.randint(1500, 2600)
        gems = random.randint(4, 8)
        medals = random.randint(4, 8)
        xp = random.randint(65, 110)
        rarity = CHEST_NAMES[chest_id]
        bonus_item_chance = 0.45

    elif chest_id == "epic_chest":
        gold = random.randint(750, 1400)
        gems = random.randint(2, 5)
        medals = random.randint(2, 5)
        xp = random.randint(35, 70)
        rarity = CHEST_NAMES[chest_id]
        bonus_item_chance = 0.32

    elif chest_id == "rare_chest":
        gold = random.randint(350, 850)
        gems = 1 if random.random() < 0.65 else 2
        medals = random.randint(1, 3)
        xp = random.randint(18, 38)
        rarity = CHEST_NAMES[chest_id]
        bonus_item_chance = 0.22

    else:
        gold = random.randint(150, 425)
        gems = 0 if random.random() < 0.65 else 1
        medals = random.randint(0, 1)
        xp = random.randint(8, 18)
        rarity = CHEST_NAMES["common_chest"]
        bonus_item_chance = 0.12

    if random.random() < bonus_item_chance and SHOP_ITEMS:
        awarded_item = random.choice([
            item_id for item_id in SHOP_ITEMS.keys()
            if item_id not in CHEST_NAMES
        ] or list(SHOP_ITEMS.keys()))
        await add_shop_item(str(interaction.user.id), awarded_item, 1)

    await _grant(
        interaction.user,
        gold=gold,
        gems=gems,
        medals=medals,
        clan_xp=xp,
        stat_updates={"chests_opened": 1},
    )

    stored = await load_coins()
    unlocked = await _award_achievements(interaction.user, stored.get("users", {}).get(str(interaction.user.id), {}))

    item_text = f"\n🎒 Bonus item: **{SHOP_ITEMS[awarded_item]['name']}**" if awarded_item else ""

    await interaction.followup.send(
        f"📦 **{rarity} Opened**\n\n"
        f"+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**"
        f"{item_text}"
    )

    await _post_achievement_followup(interaction, unlocked)

    @bot.tree.command(name="upgradehall", description="Upgrade your Discord economy Town Hall")
    async def upgradehall(interaction: discord.Interaction):
        await interaction.response.defer()
        await _ensure_user(interaction.user, interaction.user.display_name)
        stored = await load_coins()
        entry = stored.get("users", {}).get(str(interaction.user.id), {})
        th = int(entry.get("town_hall", 1) or 1)
        if th >= 16:
            await interaction.followup.send("🏰 Your economy Town Hall is already maxed at TH16.", ephemeral=True)
            return
        cost = TH_BASE_COST * th
        xp_required = th * 100
        if int(entry.get("clan_xp", 0) or 0) < xp_required:
            await interaction.followup.send(f"❌ You need **{xp_required:,} Clan XP** to upgrade to TH{th + 1}. You currently have **{int(entry.get('clan_xp', 0) or 0):,}**.", ephemeral=True)
            return
        spend = await spend_coins(str(interaction.user.id), cost)
        if not spend.get("ok"):
            await interaction.followup.send(f"❌ You need **{cost:,} Gold** to upgrade to TH{th + 1}.", ephemeral=True)
            return

        def _update(data):
            users = data.setdefault("users", {})
            user_entry = users.setdefault(str(interaction.user.id), {})
            user_entry["town_hall"] = th + 1
            return data
        await ctx.update_json_file(ctx.COINS_FILE, _update)
        stored = await load_coins()
        unlocked = await _award_achievements(interaction.user, stored.get("users", {}).get(str(interaction.user.id), {}))
        unlock_notes = []
        for command, req in TH_UNLOCKS.items():
            if req == th + 1 and command not in {"farm", "train", "admin_view"}:
                unlock_notes.append(f"`/{command}`")
        extra = f"\nUnlocked: {' '.join(unlock_notes)}" if unlock_notes else ""
        await interaction.followup.send(f"🏰 **Town Hall Upgraded!**\nYou are now **TH{th + 1}** — title unlocked: **{_title_for_th(th + 1)}**{extra}")
        await _post_achievement_followup(interaction, unlocked)

    @bot.tree.command(name="useeconomyitem", description="Use Phase 2 economy items like potions, books, runes, and chests")
    @app_commands.describe(item="The item key to use")
    async def useeconomyitem(interaction: discord.Interaction, item: str):
        await interaction.response.defer(ephemeral=True)
        item = item.strip().lower()
        await _ensure_user(interaction.user, interaction.user.display_name)
        if item not in SHOP_ITEMS:
            await interaction.followup.send("❌ Invalid item. Use `/shop` to view available items.", ephemeral=True)
            return
        shop_item = SHOP_ITEMS[item]
        item_type = shop_item.get("type")
        if item_type not in {"raid_boost_charges", "farm_boost_charges", "cooldown_clear", "xp_grant", "gold_grant", "legend_chest"}:
            await interaction.followup.send("ℹ️ That item is handled by `/useitem` or triggers passively.", ephemeral=True)
            return
        if not await consume_shop_item(str(interaction.user.id), item):
            await interaction.followup.send(f"❌ You do not own **{shop_item['name']}** yet. Buy it with `/buy {item}`.", ephemeral=True)
            return
        if item_type == "raid_boost_charges":
            charges = int(shop_item.get("charges", 3) or 3)
            await _add_boost_charges(str(interaction.user.id), "training_potion", charges)
            await interaction.followup.send(f"🧪 **{shop_item['name']} activated.** Your next **{charges}** raids get boosted.", ephemeral=True)
            return
        if item_type == "farm_boost_charges":
            charges = int(shop_item.get("charges", 4) or 4)
            await _add_boost_charges(str(interaction.user.id), "resource_potion", charges)
            await interaction.followup.send(f"🧪 **{shop_item['name']} activated.** Your next **{charges}** farm runs get boosted.", ephemeral=True)
            return
        if item_type == "cooldown_clear":
            if item == "builder_potion":
                remaining = await _cooldown_check(
                    str(interaction.user.id),
                    "builder_potion",
                    30 * 60
                )

                if remaining > 0:
                    await add_shop_item(str(interaction.user.id), item, 1)
                    await interaction.followup.send(
                        f"⏳ Builder Potion can only be used once every 30 minutes.\n"
                        f"Try again in **{_fmt_remaining(remaining)}**.",
                        ephemeral=True
                    )
                    return

                await _stamp_cooldown(str(interaction.user.id), "builder_potion")

            await _clear_cooldowns(str(interaction.user.id), ["raid"])
            await interaction.followup.send(
                f"⏩ **{shop_item['name']} used.** Your raid cooldown was cleared.",
                ephemeral=True
            )
            return

        if item_type == "xp_grant":
            if item == "book_of_heroes":
                remaining = await _cooldown_check(
                    str(interaction.user.id),
                    "book_of_heroes",
                    24 * 60 * 60
                )

                if remaining > 0:
                    await add_shop_item(str(interaction.user.id), item, 1)
                    await interaction.followup.send(
                        f"⏳ Book of Heroes can only be used once every 24 hours.\n"
                        f"Try again in **{_fmt_remaining(remaining)}**.",
                        ephemeral=True
                    )
                    return

                await _stamp_cooldown(str(interaction.user.id), "book_of_heroes")

            xp = int(shop_item.get("clan_xp", 250) or 250)
            await _grant(interaction.user, clan_xp=xp)
            await interaction.followup.send(
                f"📖 **{shop_item['name']} used.** +**{xp:,} Clan XP**",
                ephemeral=True
            )
            return

        if item_type == "gold_grant":
            if item == "rune_of_gold":
                remaining = await _cooldown_check(
                    str(interaction.user.id),
                    "rune_of_gold",
                    24 * 60 * 60
                )

                if remaining > 0:
                    await add_shop_item(str(interaction.user.id), item, 1)
                    await interaction.followup.send(
                        f"⏳ Rune of Gold can only be used once every 24 hours.\n"
                        f"Try again in **{_fmt_remaining(remaining)}**.",
                        ephemeral=True
                    )
                    return

                await _stamp_cooldown(str(interaction.user.id), "rune_of_gold")

            gold = int(shop_item.get("gold", 2500) or 2500)

            await _grant(
                interaction.user,
                gold=gold
            )

            await interaction.followup.send(
                f"🪙 **{shop_item['name']} used.** +**{gold:,} Gold**",
                ephemeral=True
            )
            return

        if item_type == "legend_chest":
            entry = (await load_coins()).get("users", {}).get(str(interaction.user.id), {})
            th = int(entry.get("town_hall", 1) or 1)

            if th < TH_UNLOCKS["legend_chest"]:
                await add_shop_item(str(interaction.user.id), item, 1)
                await interaction.followup.send(
                    _th_locked_message("Legend Chest", TH_UNLOCKS["legend_chest"]),
                    ephemeral=True
                )
                return

            remaining = await _cooldown_check(
                str(interaction.user.id),
                "legend_chest",
                24 * 60 * 60
            )

            if remaining > 0:
                await add_shop_item(str(interaction.user.id), item, 1)
                await interaction.followup.send(
                    f"⏳ Legend Chest can only be opened once every 24 hours.\n"
                    f"Try again in **{_fmt_remaining(remaining)}**.",
                    ephemeral=True
                )
                return

            await _stamp_cooldown(str(interaction.user.id), "legend_chest")

            gold = random.randint(750, 1750)
            gems = random.randint(4, 9)
            medals = random.randint(4, 8)
            xp = random.randint(75, 150)

            safe_bonus_items = [
                "lucky_charm",
                "clutch_boost",
                "mvp_token",
                "high_roller",
                "loot_shield",
                "drop_reroll",
                "war_banner",
                "training_potion",
                "resource_potion",
                "builder_potion",
            ]

            available_bonus_items = [
                key for key in safe_bonus_items
                if key in SHOP_ITEMS
            ]

            bonus_item = random.choice(available_bonus_items) if available_bonus_items else None

            if bonus_item:
                await add_shop_item(str(interaction.user.id), bonus_item, 1)

            await _grant(
                interaction.user,
                gold=gold,
                gems=gems,
                medals=medals,
                clan_xp=xp,
                stat_updates={"chests_opened": 1}
            )

            bonus_text = ""
            if bonus_item:
                bonus_text = f"\n🎒 Bonus item: **{SHOP_ITEMS[bonus_item]['name']}**"

            await interaction.followup.send(
                f"👑 **Legend Chest Opened!**\n"
                f"+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**"
                f"{bonus_text}",
                ephemeral=False
            )
            return

    @useeconomyitem.autocomplete("item")
    async def useeconomyitem_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        choices = []
        for item_key, item in SHOP_ITEMS.items():
            if item.get("type") not in {"raid_boost_charges", "farm_boost_charges", "cooldown_clear", "xp_grant", "gold_grant", "legend_chest"}:
                continue
            if current in item_key.lower() or current in item["name"].lower():
                choices.append(app_commands.Choice(name=f"{item['name']} ({item_key})", value=item_key))
        return choices[:25]

    @bot.tree.command(name="achievements", description="View your economy achievements")
    @app_commands.describe(member="Optional member to view")
    async def achievements(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        await _ensure_user(target, getattr(target, "display_name", None))
        stored = await load_coins()
        entry = stored.get("users", {}).get(str(target.id), {})
        owned = set(entry.get("achievements", []) or [])
        lines = []
        for key, ach in ACHIEVEMENTS.items():
            mark = "✅" if key in owned else "⬜"
            lines.append(f"{mark} **{ach['name']}** — {ach['desc']} Reward: {ach['reward']:,} Gold")
        embed = discord.Embed(title=f"🏆 {target.display_name}'s Achievements", description="\n".join(lines), color=0xF1C40F)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="village", description="View your or another member's Clash economy profile")
    @app_commands.describe(member="Optional member to view")
    async def village(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        await _ensure_user(target, getattr(target, "display_name", None))
        stored = await load_coins()
        data = stored.get("users", {}).get(str(target.id), {})
        stats = data.get("stats", {}) if isinstance(data, dict) else {}
        boosts = data.get("boosts", {}) if isinstance(data, dict) else {}
        th = int(data.get("town_hall", 1) or 1)
        embed = discord.Embed(title=f"🏰 {target.display_name}'s Village", color=0x3498DB)
        embed.add_field(name="Town Hall", value=f"TH{th}", inline=True)
        embed.add_field(name="Title", value=_title_for_th(th), inline=True)
        embed.add_field(name="Gold", value=f"{int(data.get('balance', 0) or 0):,}", inline=True)
        embed.add_field(name="Gems", value=f"{int(data.get('gems', 0) or 0):,}", inline=True)
        embed.add_field(name="Raid Medals", value=f"{int(data.get('raid_medals', 0) or 0):,}", inline=True)
        embed.add_field(name="Clan XP", value=f"{int(data.get('clan_xp', 0) or 0):,}", inline=True)
        if th >= TH_UNLOCKS["dark_elixir"] or int(data.get("dark_elixir", 0) or 0) > 0:
            embed.add_field(name="Dark Elixir", value=f"{int(data.get('dark_elixir', 0) or 0):,}", inline=True)
        embed.add_field(name="Daily Streak", value=f"{int(data.get('daily_streak', 0) or 0)} day(s)", inline=True)
        embed.add_field(name="Raid Record", value=f"{int(stats.get('raid_wins', 0) or 0)} wins / {int(stats.get('raids', 0) or 0)} raids", inline=True)
        active_boosts = ", ".join(f"{k.replace('_', ' ').title()} x{v}" for k, v in boosts.items()) or "None"
        embed.add_field(name="Active Boost Charges", value=active_boosts, inline=False)
        embed.add_field(name="Achievements", value=f"{len(data.get('achievements', []) or [])}/{len(ACHIEVEMENTS)} unlocked", inline=True)
        embed.add_field(name="Linked Accounts", value=await _linked_accounts_text(str(target.id)), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="economyadmin", description="Leader tools for fixing and testing the economy")
    @app_commands.describe(action="givegold, takegold, setth, resetcooldowns, giveitem, resetuser, stats", member="Target member", amount="Amount or TH level", item="Item key for giveitem")
    async def economyadmin(interaction: discord.Interaction, action: str, member: discord.Member | None = None, amount: int = 0, item: str = ""):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        action = action.strip().lower()
        target = member or interaction.user
        await _ensure_user(target, target.display_name)
        if action == "stats":
            stored = await load_coins()
            users = stored.get("users", {})
            total_gold = sum(int(u.get("balance", 0) or 0) for u in users.values() if isinstance(u, dict))
            total_xp = sum(int(u.get("clan_xp", 0) or 0) for u in users.values() if isinstance(u, dict))
            await interaction.response.send_message(f"📊 **Economy Stats**\nUsers: **{len(users)}**\nTotal Gold: **{total_gold:,}**\nTotal Clan XP: **{total_xp:,}**", ephemeral=True)
            return
        if action == "givegold":
            await _grant(target, gold=max(0, amount))
            await interaction.response.send_message(f"✅ Gave **{amount:,} Gold** to {target.mention}.", ephemeral=True)
            return
        if action == "takegold":
            await _grant(target, gold=-max(0, amount))
            await interaction.response.send_message(f"✅ Took up to **{amount:,} Gold** from {target.mention}.", ephemeral=True)
            return
        if action == "setth":
            th = max(1, min(16, int(amount or 1)))
            def _update(stored):
                users = stored.setdefault("users", {})
                entry = users.setdefault(str(target.id), {})
                entry["town_hall"] = th
                return stored
            await ctx.update_json_file(ctx.COINS_FILE, _update)
            await interaction.response.send_message(f"✅ Set {target.mention} to **TH{th}**.", ephemeral=True)
            return
        if action == "resetcooldowns":
            await _clear_cooldowns(str(target.id), ["daily", "farm", "raid", "train"])
            await interaction.response.send_message(f"✅ Reset economy cooldowns for {target.mention}.", ephemeral=True)
            return
        if action == "giveitem":
            item = item.strip().lower()
            if item not in SHOP_ITEMS:
                await interaction.response.send_message("❌ Invalid item key.", ephemeral=True)
                return
            await add_shop_item(str(target.id), item, max(1, amount or 1))
            await interaction.response.send_message(f"✅ Gave {target.mention} **{max(1, amount or 1)}x {SHOP_ITEMS[item]['name']}**.", ephemeral=True)
            return
        if action == "resetuser":
            def _update(stored):
                users = stored.setdefault("users", {})
                users.pop(str(target.id), None)
                return stored
            await ctx.update_json_file(ctx.COINS_FILE, _update)
            await interaction.response.send_message(f"✅ Reset economy data for {target.mention}.", ephemeral=True)
            return
        await interaction.response.send_message("❌ Unknown action. Use: givegold, takegold, setth, resetcooldowns, giveitem, resetuser, stats.", ephemeral=True)

    @economyadmin.autocomplete("action")
    async def economyadmin_action_autocomplete(interaction: discord.Interaction, current: str):
        actions = ["givegold", "takegold", "setth", "resetcooldowns", "giveitem", "resetuser", "stats"]
        return [app_commands.Choice(name=a, value=a) for a in actions if current.lower() in a][:25]

    @economyadmin.autocomplete("item")
    async def economyadmin_item_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{v['name']} ({k})", value=k) for k, v in SHOP_ITEMS.items() if current in k.lower() or current in v["name"].lower()][:25]

    @bot.tree.command(name="economyhelp", description="Show the expanded Clash economy command loop")
    async def economyhelp(interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ Clash Economy Commands", color=0x9B59B6)
        embed.description = "Build your mini village inside Discord: collect, farm, raid, open chests, upgrade, unlock achievements, and flex the leaderboard."
        embed.add_field(name="Earn", value="`/daily` `/farm` `/raid` `/train`", inline=False)
        embed.add_field(name="Spend", value="`/shop` `/buy` `/useitem` `/useeconomyitem` `/openchest` `/upgradehall`", inline=False)
        embed.add_field(name="Flex", value="`/village` `/achievements` `/balance` `/inventory` `/coinleaderboard`", inline=False)
        embed.add_field(name="Town Hall Unlocks", value="TH3 `/raid` • TH5 `/openchest` • TH7 better chest odds/Legend Chest • TH9 Dark Elixir", inline=False)
        embed.add_field(name="Leader Tools", value="`/economyadmin`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
