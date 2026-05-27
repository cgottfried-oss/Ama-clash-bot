from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.service import normalize_hero_loadouts, unlock_hero
from clash_mmo.game.state import load_mmo_state, update_mmo_state


RAID_USER_COOLDOWN = 2 * 60 * 60
EVENT_DURATION = 24 * 60 * 60

HEROES = {
    "king": {"name": "King", "unlock_th": 3, "base_cost": 600, "stat": "raid_power"},
    "queen": {"name": "Queen", "unlock_th": 5, "base_cost": 900, "stat": "crit"},
    "warden": {"name": "Warden", "unlock_th": 7, "base_cost": 1300, "stat": "shield"},

    # Royal Champion is intentionally disabled for now.
    # Re-enable after creating Royal Champion gear in gear_catalog.py.
    # "royal_champion": {
    #     "name": "Royal Champion",
    #     "unlock_th": 10,
    #     "base_cost": 1800,
    #     "stat": "steal",
    # },
}

EVENTS = {
    "goblin_invasion": {
        "name": "Goblin Invasion",
        "description": "+25% /raiduser steal cap and +25% boss/war event rewards while active.",
    },
    "double_loot": {
        "name": "Double Loot Weekend",
        "description": "+25% hero event rewards and season XP gains while active.",
    },
    "trader_weekend": {
        "name": "Trader Weekend",
        "description": "Hero upgrade costs are reduced by 20% while active.",
    },
}


def _now() -> int:
    return int(time.time())


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _fmt_remaining(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def _ensure_pvp_state(data: dict) -> dict:
    pvp = data.setdefault("pvp", {})
    pvp.setdefault("wars", {})
    pvp.setdefault("events", {})
    pvp.setdefault("bounties", {})
    pvp.setdefault("raid_history", [])
    return pvp


def register_pvp_commands(bot, ctx):
    COINS_FILE = ctx.COINS_FILE
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file
    spend_coins = ctx.spend_coins
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID

    def _is_admin(member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in member.roles)

    async def _load_state():
        data = await load_mmo_state(ctx)
        _ensure_pvp_state(data)
        return data

    async def _get_profile(user_id: str, name: str):
        data = await load_mmo_state(ctx)
        return ensure_player_profile(data, str(user_id), name)

    async def _get_mmo_user(user_id: str, name: str = "Unknown"):
        data = await load_mmo_state(ctx)

        profile = ensure_player_profile(
            data,
            str(user_id),
            name,
        )

        profile.setdefault("town_hall", 1)
        profile.setdefault("gold", 0)
        profile.setdefault("gems", 0)
        profile.setdefault("raid_medals", 0)
        profile.setdefault("clan_xp", 0)
        profile.setdefault("heroes", {})
        profile.setdefault("stats", {})
        profile.setdefault("cooldowns", {})
        profile.setdefault("pvp", {})

        return profile

    async def _grant_user(user_id: str, *, gold=0, gems=0, medals=0, clan_xp=0, dark_elixir=0, name="Unknown"):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(user_id),
                name,
            )

            profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + int(gold))
            profile["gems"] = max(0, int(profile.get("gems", 0) or 0) + int(gems))
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + int(medals))
            profile["clan_xp"] = max(0, int(profile.get("clan_xp", 0) or 0) + int(clan_xp))

            # Keep this ignored for now. Dark elixir is not part of the cleaned MMO economy.
            profile.setdefault("stats", {})
            profile.setdefault("cooldowns", {})
            profile.setdefault("pvp", {})

            return state

        await update_mmo_state(ctx, _update)

    async def _active_event_key():
        data = await _load_state()
        active = data.get("pvp", {}).get("events", {}).get("active")
        if not active:
            return None
        if int(active.get("ends_at", 0) or 0) <= _now():
            return None
        return active.get("key")

    async def _hero_levels(user_id: str, name: str = "Unknown"):
        profile = await _get_mmo_user(user_id, name)
        heroes = normalize_hero_loadouts(profile)

        levels = {}

        for hero_id in HEROES:
            hero_data = heroes.get(hero_id)

            if isinstance(hero_data, dict):
                levels[hero_id] = int(hero_data.get("level", 1) or 1)
            else:
                levels[hero_id] = 0

        return levels

    async def _hero_power(user_id: str, name: str = "Unknown"):
        levels = await _hero_levels(user_id, name)
        return sum(levels.values())

    @bot.tree.command(name="raiduser", description="Raid another member's village for Gold")
    @app_commands.describe(target="Member to raid")
    async def raiduser(interaction: discord.Interaction, target: discord.Member):
        if target.bot or target.id == interaction.user.id:
            await interaction.response.send_message("❌ Pick a real member other than yourself.", ephemeral=True)
            return
        attacker = await _get_mmo_user(str(interaction.user.id), interaction.user.display_name)
        defender = await _get_mmo_user(str(target.id), target.display_name)
        if int(attacker.get("town_hall", 1) or 1) < 4:
            await interaction.response.send_message("🔒 `/raiduser` unlocks at TH4.", ephemeral=True)
            return
        if int(defender.get("gold", 0) or 0) < 100:
            await interaction.response.send_message(f"❌ {target.mention} does not have enough Gold worth raiding.", ephemeral=True)
            return
        data = await _load_state()
        attacker_profile = ensure_player_profile(data, str(interaction.user.id), interaction.user.display_name)
        defender_profile = ensure_player_profile(data, str(target.id), target.display_name)
        user_state = attacker_profile.setdefault("pvp", {})
        last = int(user_state.get("last_raiduser", 0) or 0)
        if _now() - last < RAID_USER_COOLDOWN:
            await interaction.response.send_message(f"⏳ Your army is regrouping. Try again in **{_fmt_remaining(RAID_USER_COOLDOWN - (_now() - last))}**.", ephemeral=True)
            return
        atk_power = int(attacker.get("town_hall", 1) or 1) + await _hero_power(str(interaction.user.id), interaction.user.display_name)
        def_power = int(defender.get("town_hall", 1) or 1) + await _hero_power(str(target.id), target.display_name)
        chance = max(0.20, min(0.75, 0.45 + ((atk_power - def_power) * 0.03)))
        success = random.random() < chance
        event = await _active_event_key()
        cap_pct = 0.08 if event != "goblin_invasion" else 0.10
        steal_cap = max(50, int(int(defender.get("gold", 0) or 0) * cap_pct))
        amount = random.randint(50, steal_cap)
        if success:
            await _grant_user(str(target.id), gold=-amount, name=target.display_name)
            await _grant_user(str(interaction.user.id), gold=amount, clan_xp=20, name=interaction.user.display_name)
            msg = f"⚔️ {interaction.user.mention} raided {target.mention} and stole **{amount:,} Gold**!"
        else:
            penalty = min(int(attacker.get("gold", 0) or 0), max(25, amount // 3))
            await _grant_user(str(interaction.user.id), gold=-penalty, clan_xp=8, name=interaction.user.display_name)
            msg = f"🛡️ {target.mention}'s defenses held. {interaction.user.mention} lost **{penalty:,} Gold**."
        def _update(state):
            pvp = _ensure_pvp_state(state)
            a = ensure_player_profile(state, str(interaction.user.id), interaction.user.display_name).setdefault("pvp", {})
            d = ensure_player_profile(state, str(target.id), target.display_name).setdefault("pvp", {})
            a["last_raiduser"] = _now()
            d["revenge_target"] = str(interaction.user.id)
            d["revenge_until"] = _now() + 24 * 60 * 60
            history = pvp.setdefault("raid_history", [])
            history.append({"at": _now(), "attacker": str(interaction.user.id), "target": str(target.id), "success": success, "amount": amount})
            pvp["raid_history"] = history[-100:]
            return state
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(msg + f"\nSuccess chance was about **{int(chance * 100)}%**.")

    @bot.tree.command(name="revenge", description="Revenge raid the last member who raided you")
    async def revenge(interaction: discord.Interaction):
        data = await _load_state()
        profile = ensure_player_profile(data, str(interaction.user.id), interaction.user.display_name)
        state = profile.setdefault("pvp", {})
        target_id = state.get("revenge_target")
        until = int(state.get("revenge_until", 0) or 0)
        if not target_id or until <= _now():
            await interaction.response.send_message("No active revenge target.", ephemeral=True)
            return
        target = interaction.guild.get_member(int(target_id)) if interaction.guild else None
        if not target:
            await interaction.response.send_message("Your revenge target is not available in this server.", ephemeral=True)
            return
        await raiduser.callback(interaction, target)

    @bot.tree.command(name="bounty", description="Place a Gold bounty on a member")
    @app_commands.describe(target="Member to place bounty on", amount="Gold bounty amount")
    async def bounty(interaction: discord.Interaction, target: discord.Member, amount: int):
        if target.bot or target.id == interaction.user.id:
            await interaction.response.send_message("❌ Pick another real member.", ephemeral=True)
            return
        amount = max(100, int(amount or 0))
        spend = await spend_coins(str(interaction.user.id), amount)
        if not spend.get("ok"):
            await interaction.response.send_message(f"❌ You need **{amount:,} Gold**.", ephemeral=True)
            return
        def _update(state):
            pvp = _ensure_pvp_state(state)
            bounties = pvp.setdefault("bounties", {})
            entry = bounties.setdefault(str(target.id), {"amount": 0, "placed_by": []})
            entry["amount"] = int(entry.get("amount", 0) or 0) + amount
            entry.setdefault("placed_by", []).append(str(interaction.user.id))
            return state
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"🎯 {interaction.user.mention} placed a **{amount:,} Gold** bounty on {target.mention}.")

    @bot.tree.command(name="heroes", description="View your hero roster")
    @app_commands.describe(member="Optional member to view")
    async def heroes(interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        profile = await _get_mmo_user(str(target.id), target.display_name)

        town_hall = int(profile.get("town_hall", 1) or 1)
        heroes_data = normalize_hero_loadouts(profile)

        unlocked_lines = []
        locked_lines = []

        for hero_id, cfg in HEROES.items():
            hero_data = heroes_data.get(hero_id)

            if isinstance(hero_data, dict):
                level = int(hero_data.get("level", 1) or 1)
                active_marker = " ⭐ Active" if profile.get("active_hero") == hero_id else ""
                unlocked_lines.append(
                    f"**{cfg['name']}** — Lv.{level}{active_marker}"
                )
            else:
                if town_hall >= int(cfg["unlock_th"]):
                    locked_lines.append(
                        f"**{cfg['name']}** — Available at TH{cfg['unlock_th']} but not unlocked"
                    )
                else:
                    locked_lines.append(
                        f"🔒 **{cfg['name']}** — Unlocks TH{cfg['unlock_th']}"
                    )

        description_parts = []

        if unlocked_lines:
            description_parts.append("**Unlocked Heroes**\n" + "\n".join(unlocked_lines))

        if locked_lines:
            description_parts.append("**Locked Heroes**\n" + "\n".join(locked_lines))

        if not description_parts:
            description_parts.append("No heroes available.")

        total_power = 0

        for hero_id in HEROES:
            hero_data = heroes_data.get(hero_id)

            if isinstance(hero_data, dict):
                total_power += int(hero_data.get("level", 1) or 1)

        embed = discord.Embed(
            title=f"🦸 {target.display_name}'s Heroes",
            description="\n\n".join(description_parts),
            color=0x9B59B6,
        )

        embed.add_field(
            name="Town Hall",
            value=f"TH{town_hall}",
            inline=True,
        )

        embed.add_field(
            name="Total Hero Power",
            value=str(total_power),
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="upgradehero", description="Upgrade one of your heroes")
    @app_commands.describe(hero="Hero key to upgrade")
    async def upgradehero(interaction: discord.Interaction, hero: str):
        key = hero.strip().lower()

        if key not in HEROES:
            await interaction.response.send_message("❌ Invalid hero.", ephemeral=True)
            return

        cfg = HEROES[key]
        profile = await _get_mmo_user(str(interaction.user.id), interaction.user.display_name)
        town_hall = int(profile.get("town_hall", 1) or 1)

        if town_hall < int(cfg["unlock_th"]):
            await interaction.response.send_message(
                f"🔒 {cfg['name']} unlocks at TH{cfg['unlock_th']}.",
                ephemeral=True,
            )
            return

        heroes_data = normalize_hero_loadouts(profile)
        hero_data = heroes_data.get(key)

        if not isinstance(hero_data, dict):
            def _unlock_update(state):
                profile_to_update = ensure_player_profile(
                    state,
                    str(interaction.user.id),
                    interaction.user.display_name,
                )
                unlock_hero(profile_to_update, key)
                return state

            await update_mmo_state(ctx, _unlock_update)
            hero_data = {"level": 1}

        current = int(hero_data.get("level", 1) or 1)
        event = await _active_event_key()
        cost = int(cfg["base_cost"] * (current + 1))

        if event == "trader_weekend":
            cost = int(cost * 0.8)

        current_gold = int(profile.get("gold", 0) or 0)

        if current_gold < cost:
            await interaction.response.send_message(
                f"❌ You need **{cost:,} Gold** to upgrade {cfg['name']} to Lv.{current + 1}.",
                ephemeral=True,
            )
            return

        def _update(state):
            profile_to_update = ensure_player_profile(
                state,
                str(interaction.user.id),
                interaction.user.display_name,
            )

            profile_to_update["gold"] = max(0, int(profile_to_update.get("gold", 0) or 0) - cost)

            heroes = normalize_hero_loadouts(profile_to_update)
            hero_to_update = heroes.setdefault(
                key,
                {
                    "level": 1,
                    "abilities": [],
                    "equipped_ability": None,
                    "equipment": {},
                },
            )

            hero_to_update["level"] = current + 1

            if not profile_to_update.get("active_hero"):
                profile_to_update["active_hero"] = key

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"🦸 **{cfg['name']} upgraded to Lv.{current + 1}!** Cost: **{cost:,} Gold**"
        )

    @upgradehero.autocomplete("hero")
    async def upgradehero_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{cfg['name']} ({key})", value=key) for key, cfg in HEROES.items() if current in key or current in cfg["name"].lower()][:25]

    @bot.tree.command(name="startwar2", description="Leader tool: start a Clan Wars 2.0 season match")
    @app_commands.describe(opponent="Opponent clan name")
    async def startwar2(interaction: discord.Interaction, opponent: str = "Enemy Clan"):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        season = _month_key()
        def _update(state):
            pvp = _ensure_pvp_state(state)
            wars = pvp.setdefault("wars", {})
            wars[season] = {
                "opponent": opponent.strip()[:80] or "Enemy Clan",
                "started_at": _now(),
                "our_points": 0,
                "enemy_points": random.randint(100, 300),
                "attacks": {},
                "ended": False,
            }
            return state
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"⚔️ **Clan Wars 2.0 Started** vs **{opponent}**\nMembers can use `/war2attack` to earn war points.")

    @bot.tree.command(name="war2attack", description="Make a Clan Wars 2.0 attack for points")
    async def war2attack(interaction: discord.Interaction):
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war or war.get("ended"):
            await interaction.response.send_message("No active Clan Wars 2.0 match. Leaders can start one with `/startwar2`.", ephemeral=True)
            return
        attacks = war.setdefault("attacks", {})
        user_attacks = int(attacks.get(str(interaction.user.id), {}).get("count", 0) or 0)
        if user_attacks >= 2:
            await interaction.response.send_message("You already used your 2 War 2.0 attacks this match.", ephemeral=True)
            return
        profile = await _get_mmo_user(str(interaction.user.id), interaction.user.display_name)
        th = int(profile.get("town_hall", 1) or 1)
        hero_power = await _hero_power(str(interaction.user.id), interaction.user.display_name)
        points = random.randint(60, 130) + th * 8 + hero_power * 6
        stars = 1 if points < 120 else 2 if points < 190 else 3
        def _update(state):
            pvp_state = _ensure_pvp_state(state)
            w = pvp_state.setdefault("wars", {}).setdefault(season, war)
            a = w.setdefault("attacks", {}).setdefault(str(interaction.user.id), {"count": 0, "points": 0, "name": interaction.user.display_name})
            a["count"] = int(a.get("count", 0) or 0) + 1
            a["points"] = int(a.get("points", 0) or 0) + points
            a["name"] = interaction.user.display_name
            w["our_points"] = int(w.get("our_points", 0) or 0) + points
            w["enemy_points"] = int(w.get("enemy_points", 0) or 0) + random.randint(20, 80)
            return state
        await update_mmo_state(ctx, _update)
        await _grant_user(str(interaction.user.id), gold=points * 3, clan_xp=points // 4, medals=stars, name=interaction.user.display_name)
        await interaction.response.send_message(f"⚔️ **War 2.0 Attack Complete**\nResult: **{stars}⭐** | +**{points} War Points**\nRewards: **{points * 3:,} Gold**, **{points // 4} XP**, **{stars} Medals**")

    @bot.tree.command(name="war2status", description="View Clan Wars 2.0 status")
    async def war2status(interaction: discord.Interaction):
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war:
            await interaction.response.send_message("No active Clan Wars 2.0 match.", ephemeral=True)
            return
        attacks = war.get("attacks", {}) or {}
        top = sorted(attacks.items(), key=lambda item: int(item[1].get("points", 0) or 0), reverse=True)[:10]
        lines = [f"<@{uid}> — **{info.get('points', 0)} pts** ({info.get('count', 0)}/2 attacks)" for uid, info in top] or ["No attacks yet."]
        embed = discord.Embed(title=f"⚔️ War 2.0 vs {war.get('opponent')}", color=0xE74C3C)
        embed.add_field(name="Score", value=f"Us: **{int(war.get('our_points', 0) or 0):,}**\nEnemy: **{int(war.get('enemy_points', 0) or 0):,}**", inline=True)
        embed.add_field(name="Ended", value="Yes" if war.get("ended") else "No", inline=True)
        embed.add_field(name="Top Attackers", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="endwar2", description="Leader tool: end current Clan Wars 2.0 match")
    async def endwar2(interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war:
            await interaction.response.send_message("No War 2.0 match to end.", ephemeral=True)
            return
        our = int(war.get("our_points", 0) or 0)
        enemy = int(war.get("enemy_points", 0) or 0)
        won = our >= enemy
        bonus = 1000 if won else 300
        for uid, info in (war.get("attacks", {}) or {}).items():
            await _grant_user(uid, gold=bonus, clan_xp=100 if won else 35, name=info.get("name", "Unknown"))
        def _update(state):
            pvp_state = _ensure_pvp_state(state)
            w = pvp_state.setdefault("wars", {}).setdefault(season, war)
            w["ended"] = True
            w["ended_at"] = _now()
            w["result"] = "win" if won else "loss"
            return state
        await update_mmo_state(ctx, _update)
        await interaction.response.send_message(f"🏁 **War 2.0 Ended**\nResult: **{'WIN' if won else 'LOSS'}**\nFinal Score: **{our:,} - {enemy:,}**\nParticipant bonus: **{bonus:,} Gold**")

    @bot.tree.command(name="startevent", description="Leader tool: start a procedural economy event")
    @app_commands.describe(event="Event key")
    async def startevent(interaction: discord.Interaction, event: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        key = event.strip().lower()
        if key not in EVENTS:
            await interaction.response.send_message("❌ Invalid event.", ephemeral=True)
            return
        def _update(state):
            pvp = _ensure_pvp_state(state)
            pvp.setdefault("events", {})["active"] = {"key": key, "started_at": _now(), "ends_at": _now() + EVENT_DURATION}
            return state
        await update_mmo_state(ctx, _update)
        cfg = EVENTS[key]
        await interaction.response.send_message(f"🎉 **{cfg['name']} started!**\n{cfg['description']}\nEnds in **24h**.")

    @startevent.autocomplete("event")
    async def startevent_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{cfg['name']} ({key})", value=key) for key, cfg in EVENTS.items() if current in key or current in cfg["name"].lower()][:25]

    @bot.tree.command(name="eventstatus", description="View current procedural event")
    async def eventstatus(interaction: discord.Interaction):
        data = await _load_state()
        active = data.get("pvp", {}).get("events", {}).get("active")
        if not active or int(active.get("ends_at", 0) or 0) <= _now():
            await interaction.response.send_message("No active procedural event.", ephemeral=True)
            return
        cfg = EVENTS.get(active.get("key"), {"name": active.get("key"), "description": "Unknown event"})
        await interaction.response.send_message(f"🎉 **{cfg['name']}**\n{cfg['description']}\nTime left: **{_fmt_remaining(int(active.get('ends_at', 0) or 0) - _now())}**")

    @bot.tree.command(name="pvphelp", description="Show PvP economy commands")
    async def pvphelp(interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ PvP Economy Systems", color=0x2ECC71)
        embed.add_field(name="User Raiding", value="`/raiduser` `/revenge` `/bounty`", inline=False)
        embed.add_field(name="Heroes", value="`/heroes` `/upgradehero`", inline=False)
        embed.add_field(name="Clan Wars 2.0", value="`/startwar2` `/war2attack` `/war2status` `/endwar2`", inline=False)
        embed.add_field(name="Procedural Events", value="`/startevent` `/eventstatus`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
