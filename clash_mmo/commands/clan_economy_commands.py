from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands

from clash_mmo.game.seasonal_system import (
    add_season_xp,
    current_season_key,
    load_state as load_season_state,
)


CLAN_BANK_FILE_NAME = "clan_economy.json"
BOSS_DURATION_SECONDS = 12 * 60 * 60
BOSS_ATTACK_COOLDOWN = 10 * 60

CLAN_UPGRADES = {
    "training_camp": {
        "name": "Training Camp",
        "max_level": 5,
        "base_cost": 2500,
        "desc": "Boosts clan boss damage and future raid rewards.",
    },
    "treasury": {
        "name": "Clan Treasury",
        "max_level": 5,
        "base_cost": 3000,
        "desc": "Improves clan bank prestige and future passive bonuses.",
    },
    "war_academy": {
        "name": "War Academy",
        "max_level": 5,
        "base_cost": 3500,
        "desc": "Improves boss rewards and future war economy scaling.",
    },
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


def _default_clan_state():
    return {
        "bank_gold": 0,
        "lifetime_donated": 0,
        "donors": {},
        "upgrades": {},
        "boss": None,
    }


def register_clan_economy_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file
    DATA_DIR = getattr(ctx, "DATA_DIR", "/app/data")
    CLAN_BANK_FILE = str(Path(DATA_DIR) / CLAN_BANK_FILE_NAME)
    COINS_FILE = ctx.COINS_FILE
    spend_coins = ctx.spend_coins
    add_shop_item = ctx.add_shop_item
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID

    def _is_admin(member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in member.roles)

    async def _load_clan_state():
        data = await safe_load_json(CLAN_BANK_FILE)
        if not isinstance(data, dict):
            data = {}
        default = _default_clan_state()
        for key, value in default.items():
            data.setdefault(key, value)
        return data

    async def _grant_user(user_id: str, *, gold=0, gems=0, medals=0, clan_xp=0, dark_elixir=0, name="Unknown"):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}
            users = stored.setdefault("users", {})
            entry = users.setdefault(str(user_id), {"balance": 0, "lifetime_earned": 0, "name": name})
            entry["balance"] = max(0, int(entry.get("balance", 0) or 0) + int(gold))
            entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + max(0, int(gold))
            entry["gems"] = max(0, int(entry.get("gems", 0) or 0) + int(gems))
            entry["raid_medals"] = max(0, int(entry.get("raid_medals", 0) or 0) + int(medals))
            entry["clan_xp"] = max(0, int(entry.get("clan_xp", 0) or 0) + int(clan_xp))
            entry["dark_elixir"] = max(0, int(entry.get("dark_elixir", 0) or 0) + int(dark_elixir))
            entry.setdefault("town_hall", 1)
            entry.setdefault("stats", {})
            entry.setdefault("achievements", [])
            entry["name"] = name or entry.get("name", "Unknown")
            return stored
        await update_json_file(COINS_FILE, _update)

    async def _add_season_xp(user, amount: int):
        user_id = str(user.id)
        name = getattr(user, "display_name", getattr(user, "name", "Unknown"))
        unlocked = await add_season_xp(ctx, user_id, int(amount), name)
        data = await load_season_state(ctx)
        season = current_season_key()
        entry = (
            data.get("seasons", {})
            .get(season, {})
            .get("users", {})
            .get(user_id, {})
        )
        return {
            "season": season,
            "xp": int(entry.get("season_xp", 0) or 0),
            "level": int(entry.get("battle_pass_tier", 1) or 1),
            "unlocked": unlocked,
        }

    @bot.tree.command(name="clanbank", description="View the shared clan economy bank and upgrades")
    async def clanbank(interaction: discord.Interaction):
        data = await _load_clan_state()
        upgrades = data.get("upgrades", {})
        lines = []
        for key, cfg in CLAN_UPGRADES.items():
            lvl = int(upgrades.get(key, 0) or 0)
            lines.append(f"**{cfg['name']}**: Lv.{lvl}/{cfg['max_level']} — {cfg['desc']}")
        top_donors = sorted((data.get("donors", {}) or {}).items(), key=lambda item: int(item[1].get("total", 0) or 0), reverse=True)[:5]
        donor_lines = [f"<@{uid}> — **{int(info.get('total', 0) or 0):,} Gold**" for uid, info in top_donors] or ["No donations yet."]
        embed = discord.Embed(title="🏦 Clan Bank", color=0xF1C40F)
        embed.add_field(name="Bank Gold", value=f"{int(data.get('bank_gold', 0) or 0):,}", inline=True)
        embed.add_field(name="Lifetime Donated", value=f"{int(data.get('lifetime_donated', 0) or 0):,}", inline=True)
        embed.add_field(name="Clan Upgrades", value="\n".join(lines), inline=False)
        embed.add_field(name="Top Donors", value="\n".join(donor_lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="clandonate", description="Donate Gold from your balance into the clan bank")
    @app_commands.describe(amount="Gold amount to donate")
    async def clandonate(interaction: discord.Interaction, amount: int):
        amount = int(amount or 0)
        if amount <= 0:
            await interaction.response.send_message("❌ Donation amount must be positive.", ephemeral=True)
            return

        spend = await spend_coins(str(interaction.user.id), amount)
        if not spend.get("ok"):
            await interaction.response.send_message(f"❌ You do not have **{amount:,} Gold** to donate.", ephemeral=True)
            return

        name = getattr(interaction.user, "display_name", interaction.user.name)
        user_id = str(interaction.user.id)
        day_key = _day_key()

        raw_season_xp = max(1, amount // 10)
        raw_personal_clan_xp = max(1, amount // 25)

        season_xp_cap = 250
        personal_clan_xp_cap = 100

        xp_result = {
            "season_xp": 0,
            "personal_clan_xp": 0,
            "season_used": 0,
            "personal_used": 0,
        }

        def _update(data):
            if not isinstance(data, dict):
                data = _default_clan_state()

            data.setdefault("bank_gold", 0)
            data.setdefault("lifetime_donated", 0)

            donors = data.setdefault("donors", {})
            donor = donors.setdefault(user_id, {"total": 0, "name": name})

            data["bank_gold"] = int(data.get("bank_gold", 0) or 0) + amount
            data["lifetime_donated"] = int(data.get("lifetime_donated", 0) or 0) + amount
            donor["total"] = int(donor.get("total", 0) or 0) + amount
            donor["name"] = name

            daily = data.setdefault("daily_donation_xp", {})
            day = daily.setdefault(day_key, {})
            user_daily = day.setdefault(user_id, {"season_xp": 0, "personal_clan_xp": 0})

            current_season = int(user_daily.get("season_xp", 0) or 0)
            current_personal = int(user_daily.get("personal_clan_xp", 0) or 0)

            remaining_season = max(0, season_xp_cap - current_season)
            remaining_personal = max(0, personal_clan_xp_cap - current_personal)

            awarded_season = min(raw_season_xp, remaining_season)
            awarded_personal = min(raw_personal_clan_xp, remaining_personal)

            user_daily["season_xp"] = current_season + awarded_season
            user_daily["personal_clan_xp"] = current_personal + awarded_personal

            xp_result["season_xp"] = awarded_season
            xp_result["personal_clan_xp"] = awarded_personal
            xp_result["season_used"] = user_daily["season_xp"]
            xp_result["personal_used"] = user_daily["personal_clan_xp"]

            return data

        await update_json_file(CLAN_BANK_FILE, _update)

        season = None
        if xp_result["season_xp"] > 0:
            season = await _add_season_xp(interaction.user, xp_result["season_xp"])

        if xp_result["personal_clan_xp"] > 0:
            await _grant_user(user_id, clan_xp=xp_result["personal_clan_xp"], name=name)

        cap_note = ""
        if xp_result["season_used"] >= season_xp_cap and xp_result["personal_used"] >= personal_clan_xp_cap:
            cap_note = "\n⚠️ Daily donation XP cap reached. Extra donations still help the clan bank, but give no more donation XP today."

        season_level_text = f" | Battle Pass Tier: **{season['level']}**" if season else ""

        await interaction.response.send_message(
            f"🏦 {interaction.user.mention} donated **{amount:,} Gold** to the clan bank.\n"
            f"Season XP: **+{xp_result['season_xp']}** "
            f"({xp_result['season_used']}/{season_xp_cap} daily cap){season_level_text}\n"
            f"Personal Clan XP: **+{xp_result['personal_clan_xp']}** "
            f"({xp_result['personal_used']}/{personal_clan_xp_cap} daily cap)"
            f"{cap_note}"
        )

    @bot.tree.command(name="clanupgrade", description="Spend clan bank Gold on a clan upgrade")
    @app_commands.describe(upgrade="Upgrade key to buy")
    async def clanupgrade(interaction: discord.Interaction, upgrade: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        key = upgrade.strip().lower()
        if key not in CLAN_UPGRADES:
            await interaction.response.send_message("❌ Invalid upgrade. Use autocomplete or `/clanbank`.", ephemeral=True)
            return
        cfg = CLAN_UPGRADES[key]
        result = {"ok": False, "reason": "unknown", "level": 0, "cost": 0, "bank": 0}
        def _update(data):
            if not isinstance(data, dict):
                data = _default_clan_state()
            upgrades = data.setdefault("upgrades", {})
            level = int(upgrades.get(key, 0) or 0)
            if level >= int(cfg["max_level"]):
                result["reason"] = "max"
                result["level"] = level
                return data
            cost = int(cfg["base_cost"]) * (level + 1)
            bank = int(data.get("bank_gold", 0) or 0)
            result.update({"level": level, "cost": cost, "bank": bank})
            if bank < cost:
                result["reason"] = "poor"
                return data
            data["bank_gold"] = bank - cost
            upgrades[key] = level + 1
            result.update({"ok": True, "reason": "upgraded", "level": level + 1, "bank": data["bank_gold"]})
            return data
        await update_json_file(CLAN_BANK_FILE, _update)
        if result["ok"]:
            await interaction.response.send_message(f"✅ **{cfg['name']}** upgraded to **Lv.{result['level']}**. Clan bank remaining: **{result['bank']:,} Gold**")
        elif result["reason"] == "max":
            await interaction.response.send_message(f"🏦 **{cfg['name']}** is already max level.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Need **{result['cost']:,} Gold** in clan bank. Current bank: **{result['bank']:,}**.", ephemeral=True)

    @clanupgrade.autocomplete("upgrade")
    async def clanupgrade_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{cfg['name']} ({key})", value=key) for key, cfg in CLAN_UPGRADES.items() if current in key or current in cfg["name"].lower()][:25]

    @bot.tree.command(name="startboss", description="Leader tool: start a shared clan boss raid")
    @app_commands.describe(name="Boss name", hp="Boss HP")
    async def startboss(interaction: discord.Interaction, name: str = "Goblin King", hp: int = 37500):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        hp = max(5000, min(250000, int(hp or 37500)))
        boss_name = name.strip()[:60] or "Goblin King"
        def _update(data):
            if not isinstance(data, dict):
                data = _default_clan_state()
            data["boss"] = {
                "name": boss_name,
                "max_hp": hp,
                "hp": hp,
                "started_at": _now(),
                "ends_at": _now() + BOSS_DURATION_SECONDS,
                "participants": {},
                "defeated": False,
                "rewards_claimed": False,
            }
            return data
        await update_json_file(CLAN_BANK_FILE, _update)
        await interaction.response.send_message(f"👹 **Clan Boss Started:** {boss_name}\nHP: **{hp:,}**\nUse `/bossattack` every 10 minutes to damage it!")

    @bot.tree.command(name="boss", description="View current clan boss raid status")
    async def boss(interaction: discord.Interaction):
        data = await _load_clan_state()
        boss = data.get("boss")
        if not boss:
            await interaction.response.send_message("No active clan boss. Leaders can start one with `/startboss`.", ephemeral=True)
            return
        participants = boss.get("participants", {}) or {}
        top = sorted(participants.items(), key=lambda item: int(item[1].get("damage", 0) or 0), reverse=True)[:5]
        lines = [f"<@{uid}> — **{int(info.get('damage', 0) or 0):,} dmg**" for uid, info in top] or ["No attacks yet."]
        hp = max(0, int(boss.get("hp", 0) or 0))
        max_hp = max(1, int(boss.get("max_hp", 1) or 1))
        pct = max(0, min(100, int((hp / max_hp) * 100)))
        ends_at = int(boss.get("ends_at", 0) or 0)
        embed = discord.Embed(title=f"👹 {boss.get('name', 'Clan Boss')}", color=0xE74C3C)
        embed.add_field(name="HP", value=f"{hp:,}/{max_hp:,} ({pct}%)", inline=True)
        embed.add_field(name="Time Left", value=_fmt_remaining(ends_at - _now()) if ends_at > _now() else "Expired", inline=True)
        embed.add_field(name="Top Damage", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="bossattack", description="Attack the active clan boss once every 10 minutes")
    async def bossattack(interaction: discord.Interaction):
        result = {"ok": False, "reason": "unknown"}
        name = getattr(interaction.user, "display_name", interaction.user.name)
        data = await _load_clan_state()
        boss = data.get("boss")
        if not boss:
            await interaction.response.send_message("No active clan boss right now.", ephemeral=True)
            return
        if int(boss.get("ends_at", 0) or 0) <= _now():
            await interaction.response.send_message("The clan boss event has expired.", ephemeral=True)
            return
        if bool(boss.get("defeated")) or int(boss.get("hp", 0) or 0) <= 0:
            await interaction.response.send_message("The clan boss is already defeated. Use `/claimbossrewards`.", ephemeral=True)
            return
        upgrades = data.get("upgrades", {}) or {}
        training_bonus = int(upgrades.get("training_camp", 0) or 0) * 75
        damage = random.randint(650, 1400) + training_bonus
        def _update(state):
            b = state.get("boss")
            if not b:
                result["reason"] = "missing"
                return state
            participants = b.setdefault("participants", {})
            p = participants.setdefault(str(interaction.user.id), {"damage": 0, "last_attack": 0, "name": name})
            last = int(p.get("last_attack", 0) or 0)
            if _now() - last < BOSS_ATTACK_COOLDOWN:
                result.update({"reason": "cooldown", "remaining": BOSS_ATTACK_COOLDOWN - (_now() - last)})
                return state
            p["damage"] = int(p.get("damage", 0) or 0) + damage
            p["last_attack"] = _now()
            p["name"] = name
            b["hp"] = max(0, int(b.get("hp", 0) or 0) - damage)
            if b["hp"] <= 0:
                b["defeated"] = True
            result.update({"ok": True, "damage": damage, "hp": b["hp"], "defeated": b.get("defeated", False)})
            return state
        await update_json_file(CLAN_BANK_FILE, _update)
        if result.get("reason") == "cooldown":
            await interaction.response.send_message(f"⏳ Your army needs to regroup. Try again in **{_fmt_remaining(result['remaining'])}**.", ephemeral=True)
            return
        season_xp = max(5, int(result.get("damage", 0)) // 100)
        await _add_season_xp(interaction.user, season_xp)
        defeated_text = "\n🏆 **Boss defeated!** Use `/claimbossrewards`." if result.get("defeated") else ""
        await interaction.response.send_message(f"⚔️ {interaction.user.mention} hit the boss for **{int(result.get('damage', 0)):,} damage**.\nBoss HP left: **{int(result.get('hp', 0)):,}**\nSeason XP: **+{season_xp}**{defeated_text}")

    @bot.tree.command(name="claimbossrewards", description="Claim rewards after defeating the clan boss")
    async def claimbossrewards(interaction: discord.Interaction):
        data = await _load_clan_state()
        boss = data.get("boss")
        if not boss or not boss.get("defeated"):
            await interaction.response.send_message("No defeated boss rewards are available.", ephemeral=True)
            return
        if boss.get("rewards_claimed"):
            await interaction.response.send_message("Boss rewards were already claimed.", ephemeral=True)
            return
        participants = boss.get("participants", {}) or {}
        if str(interaction.user.id) not in participants:
            await interaction.response.send_message("Only participants can trigger boss rewards.", ephemeral=True)
            return
        total_damage = sum(int(p.get("damage", 0) or 0) for p in participants.values()) or 1
        war_academy = int((data.get("upgrades", {}) or {}).get("war_academy", 0) or 0)
        reward_lines = []
        for uid, info in participants.items():
            dmg = int(info.get("damage", 0) or 0)
            share = dmg / total_damage
            gold = int(1200 + share * 6500 + war_academy * 150)
            gems = 1 + (1 if share >= 0.20 else 0)
            medals = 1 + int(share * 5)
            xp = int(60 + share * 240)
            await _grant_user(uid, gold=gold, gems=gems, medals=medals, clan_xp=xp, name=info.get("name", "Unknown"))
            legend_chest_text = ""
            if random.random() < 0.08:
                await add_shop_item(uid, "legend_chest", 1)
                legend_chest_text = ", **Legend Chest**"
            reward_lines.append(f"<@{uid}> — {dmg:,} dmg → **{gold:,} Gold**, **{gems} Gems**, **{medals} Medals**, **{xp} XP**{legend_chest_text}")
        def _update(state):
            if state.get("boss"):
                state["boss"]["rewards_claimed"] = True
            return state
        await update_json_file(CLAN_BANK_FILE, _update)
        await interaction.response.send_message("🎁 **Clan Boss Rewards Paid**\n" + "\n".join(reward_lines[:15]))
