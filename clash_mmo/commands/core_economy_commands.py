from __future__ import annotations

import random
import time
from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.state import load_mmo_state, update_mmo_state
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
    "boss_raids": 7,
    "hero_abilities": 9,
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
        return "Clan Member"
    if th >= 6:
        return "Base Builder"
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
    
    async def _mmo_profile(user: discord.Member | discord.User):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(user.id),
                getattr(user, "display_name", None) or getattr(user, "name", "Unknown"),
            )

            profile.setdefault("town_hall", 1)
            profile.setdefault("gold", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("clan_xp", 0)
            profile.setdefault("daily_streak", 0)
            profile.setdefault("cooldowns", {})
            profile.setdefault("stats", {})

            return state

        await update_mmo_state(ctx, _update)

        state = await load_mmo_state(ctx)
        return state.setdefault("players", {}).get(str(user.id), {})
        
    async def _mmo_cooldown_check(user_id: str, key: str, cooldown_seconds: int):
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        cooldowns = profile.get("cooldowns", {}) if isinstance(profile.get("cooldowns", {}), dict) else {}
        last = int(cooldowns.get(key, 0) or 0)
        remaining = cooldown_seconds - (_now() - last)
        return max(0, remaining)
        
    async def _stamp_mmo_cooldown(user_id: str, key: str):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            players = state.setdefault("players", {})
            profile = players.setdefault(str(user_id), {})
            cooldowns = profile.setdefault("cooldowns", {})
            cooldowns[key] = _now()

            return state

        await update_mmo_state(ctx, _update)
        
    async def _grant_mmo_rewards(
        user: discord.Member | discord.User,
        *,
        gold: int = 0,
        gems: int = 0,
        medals: int = 0,
        clan_xp: int = 0,
        stat_updates: dict | None = None,
    ):
        user_id = str(user.id)
        display_name = getattr(user, "display_name", None) or getattr(user, "name", "Unknown")

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                user_id,
                display_name,
            )

            profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + int(gold))
            profile["gems"] = max(0, int(profile.get("gems", 0) or 0) + int(gems))
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + int(medals))
            profile["clan_xp"] = max(0, int(profile.get("clan_xp", 0) or 0) + int(clan_xp))

            stats = profile.setdefault("stats", {})

            for key, delta in (stat_updates or {}).items():
                stats[key] = int(stats.get(key, 0) or 0) + int(delta)

            return state

        await update_mmo_state(ctx, _update)

    def _is_admin(member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in member.roles)

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
            entry["balance"] = max(0, int(entry.get("balance", 0) or 0) + int(gold))
            entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + max(0, int(gold))
            entry["gems"] = max(0, int(entry.get("gems", 0) or 0) + int(gems))
            entry["raid_medals"] = max(0, int(entry.get("raid_medals", 0) or 0) + int(medals))
            entry["clan_xp"] = max(0, int(entry.get("clan_xp", 0) or 0) + int(clan_xp))
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
            "training_potion": 2,
            "resource_potion": 2,
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

    @bot.tree.command(name="raidvillage", description="Attack a random NPC village for loot and XP")
    async def raidvillage(interaction: discord.Interaction):
        await interaction.response.defer()

        profile = await _mmo_profile(interaction.user)
        town_hall = int(profile.get("town_hall", 1) or 1)

        if town_hall < TH_UNLOCKS["raid"]:
            await interaction.followup.send(
                _th_locked_message("/raidvillage", TH_UNLOCKS["raid"]),
                ephemeral=True,
            )
            return

        remaining = await _mmo_cooldown_check(str(interaction.user.id), "raidvillage", RAID_COOLDOWN)

        if remaining > 0:
            await interaction.followup.send(
                f"⏳ Your army is not ready. Try `/raidvillage` again in **{_fmt_remaining(remaining)}**.",
                ephemeral=True,
            )
            return

        roll = random.random()
        stars = 0
        gold = 0
        gems = 0
        medals = 0
        xp = 0

        if roll < 0.12:
            result_title = "💀 Raid Failed"
            result_text = "The NPC village had stronger defenses than expected."
            xp = 3
            stat_updates = {"raidvillage_runs": 1}
        elif roll < 0.42:
            stars = 1
            result_title = "⭐ One-Star Village Raid"
            result_text = "You grabbed the Town Hall and escaped with loot."
            gold = random.randint(180, 420) + town_hall * 20
            xp = random.randint(8, 16)
            stat_updates = {"raidvillage_runs": 1, "raidvillage_wins": 1}
        elif roll < 0.82:
            stars = 2
            result_title = "⭐⭐ Two-Star Village Raid"
            result_text = "Solid hit. Storages cracked, heroes survived."
            gold = random.randint(350, 700) + town_hall * 35
            medals = 1 if random.random() < 0.35 else 0
            xp = random.randint(15, 28)
            stat_updates = {"raidvillage_runs": 1, "raidvillage_wins": 1}
        else:
            stars = 3
            result_title = "⭐⭐⭐ Triple Village Raid"
            result_text = "You crushed the NPC base and brought the loot cart home."
            gold = random.randint(725, 1150) + town_hall * 50
            gems = 1 if random.random() < 0.35 else 0
            medals = random.randint(1, 3)
            xp = random.randint(30, 55)
            stat_updates = {"raidvillage_runs": 1, "raidvillage_wins": 1, "raidvillage_triples": 1}

        await _grant_mmo_rewards(
            interaction.user,
            gold=gold,
            gems=gems,
            medals=medals,
            clan_xp=xp,
            stat_updates=stat_updates,
        )

        await _stamp_mmo_cooldown(str(interaction.user.id), "raidvillage")

        await interaction.followup.send(
            f"{result_title}\n"
            f"{result_text}\n\n"
            f"+**{gold:,} Gold** | +**{gems} Gems** | +**{medals} Raid Medals** | +**{xp} Clan XP**"
        )

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

    @bot.tree.command(name="economyhelp", description="Show the Clash MMO economy command loop")
    async def economyhelp(interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ Clash MMO Economy Commands", color=0x9B59B6)
        embed.description = (
            "Build your mini village inside Discord: collect, farm, raid, earn chests, "
            "upgrade your Town Hall, unlock heroes, equip gear, and push progression."
        )

        embed.add_field(
            name="Earn",
            value="`/daily` `/farm` `/raid` `/train`",
            inline=False,
        )

        embed.add_field(
            name="Chests",
            value="`/openchest` — open Common, Rare, Epic, and Legend Chests earned from raids and boss rewards",
            inline=False,
        )

        embed.add_field(
            name="Spend / Items",
            value="`/shop` `/buy` `/useitem` `/useeconomyitem` `/upgradehall`",
            inline=False,
        )

        embed.add_field(
            name="Heroes / Gear",
            value="`/heroes` `/gear` `/lootgear` `/equipgear` `/equipability`",
            inline=False,
        )

        embed.add_field(
            name="Boss Raids",
            value="`/raidstatus` `/joinraid` `/attackraid`",
            inline=False,
        )

        embed.add_field(
            name="Flex",
            value="`/village` `/achievements` `/balance` `/inventory` `/coinleaderboard`",
            inline=False,
        )

        embed.add_field(
            name="Town Hall Unlocks",
            value=(
                "TH3 `/raid` • TH5 `/openchest` • "
                "TH7 Boss Raids + Legend Chest rewards • "
                "TH9 Hero Abilities"
            ),
            inline=False,
        )

        embed.add_field(
            name="Leader Tools",
            value="`/economyadmin`",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)