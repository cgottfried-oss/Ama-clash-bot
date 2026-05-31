from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from pathlib import Path

import discord
from shared.interactions import safe_respond
from discord import app_commands

from clash_mmo.game.seasonal_system import (
    add_season_xp,
    current_season_key,
    load_state as load_season_state,
)
from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.state import load_mmo_state, update_mmo_state


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
        def _update(state):
            if not isinstance(state, dict):
                state = {}
    
            profile = ensure_player_profile(state, str(user_id), name)
            profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + int(gold))
            profile["gems"] = max(0, int(profile.get("gems", 0) or 0) + int(gems))
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + int(medals))
            profile["clan_xp"] = max(0, int(profile.get("clan_xp", 0) or 0) + int(clan_xp))
            profile["dark_elixir"] = max(0, int(profile.get("dark_elixir", 0) or 0) + int(dark_elixir))
    
            stats = profile.setdefault("stats", {})
            if int(gold) > 0:
                stats["lifetime_gold"] = int(stats.get("lifetime_gold", 0) or 0) + int(gold)
    
            identity = profile.setdefault("identity", {})
            identity["display_name"] = name
            profile["name"] = name
    
            return state
    
        await update_mmo_state(ctx, _update)
        
    async def _spend_mmo_gold(user_id: str, amount: int, name="Unknown"):
        result = {"ok": False, "balance": 0}
    
        def _update(state):
            if not isinstance(state, dict):
                state = {}
    
            profile = ensure_player_profile(state, str(user_id), name)
            current_gold = int(profile.get("gold", 0) or 0)
            result["balance"] = current_gold
    
            if current_gold < int(amount):
                return state
    
            profile["gold"] = current_gold - int(amount)
            result["balance"] = profile["gold"]
            result["ok"] = True
    
            return state
    
        await update_mmo_state(ctx, _update)
        return result

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
        await interaction.response.defer()
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
        await safe_respond(interaction, embed=embed)

    @bot.tree.command(name="clandonate", description="Donate Gold from your balance into the clan bank")
    @app_commands.describe(amount="Gold amount to donate")
    async def clandonate(interaction: discord.Interaction, amount: int):
        await interaction.response.defer()
        amount = int(amount or 0)
        if amount <= 0:
            await safe_respond(interaction, "❌ Donation amount must be positive.", ephemeral=True)
            return

        spend = await _spend_mmo_gold(str(interaction.user.id), amount, interaction.user.display_name)
        if not spend.get("ok"):
            await safe_respond(interaction, f"❌ You do not have **{amount:,} Gold** to donate.", ephemeral=True)
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

        await safe_respond(interaction, 
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
        await interaction.response.defer()
        if not _is_admin(interaction.user):
            await safe_respond(interaction, "❌ Leaders and co-leaders only.", ephemeral=True)
            return
        key = upgrade.strip().lower()
        if key not in CLAN_UPGRADES:
            await safe_respond(interaction, "❌ Invalid upgrade. Use autocomplete or `/clanbank`.", ephemeral=True)
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
            await safe_respond(interaction, f"✅ **{cfg['name']}** upgraded to **Lv.{result['level']}**. Clan bank remaining: **{result['bank']:,} Gold**")
        elif result["reason"] == "max":
            await safe_respond(interaction, f"🏦 **{cfg['name']}** is already max level.", ephemeral=True)
        else:
            await safe_respond(interaction, f"❌ Need **{result['cost']:,} Gold** in clan bank. Current bank: **{result['bank']:,}**.", ephemeral=True)

    @clanupgrade.autocomplete("upgrade")
    async def clanupgrade_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{cfg['name']} ({key})", value=key) for key, cfg in CLAN_UPGRADES.items() if current in key or current in cfg["name"].lower()][:25]
        
        await update_json_file(CLAN_BANK_FILE, _update)
