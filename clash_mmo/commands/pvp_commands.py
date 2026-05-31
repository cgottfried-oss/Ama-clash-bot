from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.service import get_effective_profile_stats
from clash_mmo.game.matchmaking.battle import calculate_power
from clash_mmo.game.heroes import enabled_hero_ids, normalize_hero_loadouts
from clash_mmo.game.pve.world_events import (
    EVENT_DURATION,
    WORLD_EVENTS as EVENTS,
    get_active_effect,
    get_active_event_key,
    start_event,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state


RAID_USER_COOLDOWN = 3 * 60


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
    LEADER_ROLE_ID = ctx.LEADER_ROLE_ID
    CO_LEADER_ROLE_ID = ctx.CO_LEADER_ROLE_ID
    
    async def _spend_mmo_gold(user_id: str, amount: int, name: str = "Unknown"):
        amount = max(0, int(amount or 0))
        result = {
            "ok": False,
            "balance": 0,
        }

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(user_id),
                name,
            )

            current_gold = int(profile.get("gold", 0) or 0)
            result["balance"] = current_gold

            if current_gold < amount:
                return state

            profile["gold"] = current_gold - amount
            result["ok"] = True
            result["balance"] = profile["gold"]

            return state

        await update_mmo_state(ctx, _update)
        return result

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
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
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

            return state

        await update_mmo_state(ctx, _update)

        data = await load_mmo_state(ctx)
        return data.get("players", {}).get(str(user_id), {})

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
            profile.setdefault("stats", {})
            profile.setdefault("cooldowns", {})
            profile.setdefault("pvp", {})

            return state

        await update_mmo_state(ctx, _update)

    async def _active_event_key():
        data = await _load_state()
        return get_active_event_key(data)

    async def _hero_levels(user_id: str, name: str = "Unknown"):
        profile = await _get_mmo_user(user_id, name)
        heroes = normalize_hero_loadouts(profile)

        levels = {}

        for hero_id in enabled_hero_ids():
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
        # Defer immediately: this command does multiple state loads + gear stat
        # computation, which can exceed Discord's 3-second response window and
        # cause "Unknown interaction" (10062) errors. Deferring buys 15 minutes.
        await interaction.response.defer()
        if target.bot or target.id == interaction.user.id:
            await interaction.followup.send("❌ Pick a real member other than yourself.", ephemeral=True)
            return
        attacker = await _get_mmo_user(str(interaction.user.id), interaction.user.display_name)
        defender = await _get_mmo_user(str(target.id), target.display_name)
        if int(attacker.get("town_hall", 1) or 1) < 4:
            await interaction.followup.send("🔒 `/raiduser` unlocks at TH4.", ephemeral=True)
            return
        if int(defender.get("gold", 0) or 0) < 100:
            await interaction.followup.send(f"❌ {target.mention} does not have enough Gold worth raiding.", ephemeral=True)
            return
        data = await _load_state()
        attacker_profile = ensure_player_profile(data, str(interaction.user.id), interaction.user.display_name)
        defender_profile = ensure_player_profile(data, str(target.id), target.display_name)
        user_state = attacker_profile.setdefault("pvp", {})
        last = int(user_state.get("last_raiduser", 0) or 0)
        if _now() - last < RAID_USER_COOLDOWN:
            await interaction.followup.send(f"⏳ Your army is regrouping. Try again in **{_fmt_remaining(RAID_USER_COOLDOWN - (_now() - last))}**.", ephemeral=True)
            return
        # Gear-vs-gear: each side's equipped gear contributes a power score on
        # top of their Town Hall + hero power, so offensive AND defensive gear
        # both matter. Gear power is scaled down (×0.5) so it augments the
        # TH/hero base rather than dwarfing it.
        atk_gear = calculate_power(get_effective_profile_stats(attacker_profile)) * 0.5
        def_gear = calculate_power(get_effective_profile_stats(defender_profile)) * 0.5
        atk_power = int(attacker.get("town_hall", 1) or 1) + await _hero_power(str(interaction.user.id), interaction.user.display_name) + atk_gear
        def_power = int(defender.get("town_hall", 1) or 1) + await _hero_power(str(target.id), target.display_name) + def_gear
        chance = max(0.20, min(0.75, 0.45 + ((atk_power - def_power) * 0.03)))
        success = random.random() < chance
        event = await _active_event_key()
        cap_pct = 0.08 if event != "goblin_invasion" else 0.10
        steal_cap = max(50, int(int(defender.get("gold", 0) or 0) * cap_pct))
        amount = random.randint(50, steal_cap)
        shield_blocked = False
        if success:
            defender_inventory = defender_profile.setdefault("shop_inventory", {})
            guard_shields = int(defender_inventory.get("guard_shield", 0) or 0)
            if guard_shields > 0:
                shield_blocked = True
                if guard_shields == 1:
                    defender_inventory.pop("guard_shield", None)
                else:
                    defender_inventory["guard_shield"] = guard_shields - 1

                def _consume_guard_shield(state):
                    if not isinstance(state, dict):
                        state = {}
                    target_profile = ensure_player_profile(state, str(target.id), target.display_name)
                    inventory = target_profile.setdefault("shop_inventory", {})
                    shields = int(inventory.get("guard_shield", 0) or 0)
                    if shields <= 1:
                        inventory.pop("guard_shield", None)
                    else:
                        inventory["guard_shield"] = shields - 1
                    return state

                await update_mmo_state(ctx, _consume_guard_shield)
                msg = f"🛡️ {target.mention}'s **Guard Shield** blocked {interaction.user.mention}'s raid-user attack!"
            else:
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
            history.append({"at": _now(), "attacker": str(interaction.user.id), "target": str(target.id), "success": success, "shield_blocked": shield_blocked, "amount": amount})
            pvp["raid_history"] = history[-100:]
            return state
        await update_mmo_state(ctx, _update)
        await interaction.followup.send(msg + f"\nSuccess chance was about **{int(chance * 100)}%**.")

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

        spend = await _spend_mmo_gold(
            str(interaction.user.id),
            amount,
            interaction.user.display_name,
        )

        if not spend.get("ok"):
            await interaction.response.send_message(
                f"❌ You need **{amount:,} Gold** in your MMO profile.",
                ephemeral=True,
            )
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            pvp = _ensure_pvp_state(state)
            bounties = pvp.setdefault("bounties", {})

            entry = bounties.setdefault(
                str(target.id),
                {
                    "amount": 0,
                    "placed_by": [],
                },
            )

            entry["amount"] = int(entry.get("amount", 0) or 0) + amount

            placed_by = entry.setdefault("placed_by", [])
            placed_by.append(str(interaction.user.id))

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"🎯 {interaction.user.mention} placed a **{amount:,} Gold** bounty on {target.mention}."
        )

    @bot.tree.command(name="startwar", description="Leader tool: start a clan war season match")
    @app_commands.describe(opponent="Opponent clan name")
    async def startwar(interaction: discord.Interaction, opponent: str = "Enemy Clan"):
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
        await interaction.response.send_message(f"⚔️ **Clan War Started** vs **{opponent}**\nMembers can use `/warattack` to earn war points.")

    @bot.tree.command(name="warattack", description="Make a clan war attack for points")
    async def warattack(interaction: discord.Interaction):
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war or war.get("ended"):
            await interaction.response.send_message("No active clan war match. Leaders can start one with `/startwar`.", ephemeral=True)
            return
        attacks = war.setdefault("attacks", {})
        user_attacks = int(attacks.get(str(interaction.user.id), {}).get("count", 0) or 0)
        if user_attacks >= 2:
            await interaction.response.send_message("You already used your 2 war attacks this match.", ephemeral=True)
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
        war_mult = float(get_active_effect(data, "war_reward_multiplier", 1.0) or 1.0)
        war_gold = int(round(points * 3 * war_mult))
        await update_mmo_state(ctx, _update)
        await _grant_user(str(interaction.user.id), gold=war_gold, clan_xp=points // 4, medals=stars, name=interaction.user.display_name)
        event_note = f"\n🎉 Event bonus: **{int((war_mult - 1) * 100)}% extra war Gold!**" if war_mult > 1.0 else ""
        await interaction.response.send_message(f"⚔️ **War Attack Complete**\nResult: **{stars}⭐** | +**{points} War Points**\nRewards: **{war_gold:,} Gold**, **{points // 4} XP**, **{stars} Medals**{event_note}")

    @bot.tree.command(name="warstatus", description="View clan war status")
    async def warstatus(interaction: discord.Interaction):
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war:
            await interaction.response.send_message("No active clan war match.", ephemeral=True)
            return
        attacks = war.get("attacks", {}) or {}
        top = sorted(attacks.items(), key=lambda item: int(item[1].get("points", 0) or 0), reverse=True)[:10]
        lines = [f"<@{uid}> — **{info.get('points', 0)} pts** ({info.get('count', 0)}/2 attacks)" for uid, info in top] or ["No attacks yet."]
        embed = discord.Embed(title=f"⚔️ War vs {war.get('opponent')}", color=0xE74C3C)
        embed.add_field(name="Score", value=f"Us: **{int(war.get('our_points', 0) or 0):,}**\nEnemy: **{int(war.get('enemy_points', 0) or 0):,}**", inline=True)
        embed.add_field(name="Ended", value="Yes" if war.get("ended") else "No", inline=True)
        embed.add_field(name="Top Attackers", value="\n".join(lines), inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="endwar", description="Leader tool: end current Clan Wars match")
    async def endwar(interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        data = await _load_state()
        pvp = _ensure_pvp_state(data)
        season = _month_key()
        war = pvp.get("wars", {}).get(season)
        if not war:
            await interaction.response.send_message("No War match to end.", ephemeral=True)
            return
        our = int(war.get("our_points", 0) or 0)
        enemy = int(war.get("enemy_points", 0) or 0)
        won = our >= enemy
        war_mult = float(get_active_effect(data, "war_reward_multiplier", 1.0) or 1.0)
        bonus = int(round((1000 if won else 300) * war_mult))
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
        await interaction.response.send_message(f"🏁 **War Ended**\nResult: **{'WIN' if won else 'LOSS'}**\nFinal Score: **{our:,} - {enemy:,}**\nParticipant bonus: **{bonus:,} Gold**")

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
            _ensure_pvp_state(state)
            start_event(state, key)
            return state
        await update_mmo_state(ctx, _update)
        cfg = EVENTS[key]
        await interaction.response.send_message(f"🎉 **{cfg['name']} started!**\n{cfg['description']}\nEnds in **24h**.")

    @startevent.autocomplete("event")
    async def startevent_autocomplete(interaction: discord.Interaction, current: str):
        current = current.lower()
        return [app_commands.Choice(name=f"{cfg['name']} ({key})", value=key) for key, cfg in EVENTS.items() if current in key or current in get_hero_name(key).lower()][:25]

    @bot.tree.command(name="eventstatus", description="View the active world event")
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
        embed.add_field(name="Clan Wars", value="`/startwar` `/warattack` `/warstatus` `/endwar`", inline=False)
        embed.add_field(name="Procedural Events", value="`/startevent` `/eventstatus`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
