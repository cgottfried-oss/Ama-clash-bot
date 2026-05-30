from __future__ import annotations

import random

import discord

RAID_UNLOCK_TH = 7
RAID_ATTACK_COOLDOWN_SECONDS = 10 * 60
RAID_JOIN_COST = 5

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.cosmetics.service import get_equipped_cosmetic_bonuses
from clash_mmo.game.equipment.service import grant_equipment
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.pve import (
    RAID_BOSSES,
    attack_raid_boss,
    format_attack_result,
    format_raid_status,
    get_active_raid,
    get_boss_phase,
    join_raid,
    start_raid,
)

from clash_mmo.game.state import (
    load_mmo_state,
    update_mmo_state,
)


def register_raid_commands(bot, ctx):

    async def _profiles():
        data = await load_mmo_state(ctx)
        data.setdefault("players", {})
        return data

    async def _raid_attack_remaining(user_id: str, raid: dict) -> int:
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        cooldowns = profile.get("cooldowns", {}) if isinstance(profile, dict) else {}

        last_attack = int(cooldowns.get("bossattack", 0) or 0)

        mechanics = raid.get("mechanics", {}) if isinstance(raid, dict) else {}
        user_mechanics = mechanics.get(str(user_id), {}) if isinstance(mechanics, dict) else {}
        penalty = int(user_mechanics.get("cooldown_penalty_seconds", 0) or 0)

        cooldown_seconds = RAID_ATTACK_COOLDOWN_SECONDS + penalty
        remaining = cooldown_seconds - (int(ctx.now()) - last_attack)

        return max(0, remaining)

    async def _stamp_raid_attack(user_id: str, name: str = "Unknown"):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(user_id),
                name,
            )

            cooldowns = profile.setdefault("cooldowns", {})
            cooldowns["bossattack"] = int(ctx.now())

            return state

        await update_mmo_state(ctx, _update)

    async def _consume_boost_charge(user_id: str, boost_key: str) -> bool:
        consumed = False

        def _update(state):
            nonlocal consumed
            if not isinstance(state, dict):
                state = {}
            profile = ensure_player_profile(state, str(user_id), f"User {user_id}")
            boosts = profile.setdefault("boosts", {})
            charges = int(boosts.get(boost_key, 0) or 0)
            if charges > 0:
                if charges == 1:
                    boosts.pop(boost_key, None)
                else:
                    boosts[boost_key] = charges - 1
                consumed = True
            return state

        await update_mmo_state(ctx, _update)
        return consumed

    async def _has_boost_charge(user_id: str, boost_key: str) -> bool:
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        boosts = profile.get("boosts", {})
        return int(boosts.get(boost_key, 0) or 0) > 0

    async def _mmo_town_hall(user_id: str, name: str = "Unknown") -> int:
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
            profile.setdefault("elixir", 0)
            profile.setdefault("dark_elixir", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("shiny_ore", 0)
            profile.setdefault("glowy_ore", 0)
            profile.setdefault("starry_ore", 0)
            profile.setdefault("clan_xp", 0)
            profile.setdefault("cooldowns", {})
            profile.setdefault("stats", {})

            return state

        await update_mmo_state(ctx, _update)

        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})

        return int(profile.get("town_hall", 1) or 1)

    def _pick_random_boss_id() -> str:
        return random.choice(list(RAID_BOSSES.keys()))

    async def _get_active_raid():
        # Read-only: the auto-spawn loop owns raid creation now. Commands
        # only ever read the current raid; they never spawn one.
        data = await load_mmo_state(ctx)
        raids = data.setdefault("raids", {})
        return get_active_raid(raids)

    async def _grant_defeat_rewards(defeat_rewards: dict | None):
        if not defeat_rewards:
            return []
    
        reward_lines = []
    
        for user_id, reward in defeat_rewards.items():
            gold = int(reward.get("gold", 0) or 0)
            elixir = int(reward.get("elixir", 0) or 0)
            dark_elixir = int(reward.get("dark_elixir", 0) or 0)
            gems = int(reward.get("gems", 0) or 0)
            raid_medals = int(reward.get("raid_medals", 0) or 0)
            shiny_ore = int(reward.get("shiny_ore", 0) or 0)
            glowy_ore = int(reward.get("glowy_ore", 0) or 0)
            starry_ore = int(reward.get("starry_ore", 0) or 0)
            clan_xp = int(reward.get("clan_xp", 0) or 0)
            gear_drop = reward.get("gear_drop")
    
            def _update(state):
                if not isinstance(state, dict):
                    state = {}
    
                profile = ensure_player_profile(
                    state,
                    str(user_id),
                    f"User {user_id}",
                )
    
                _cos = get_equipped_cosmetic_bonuses(profile)
                _boss_pct = float(_cos.get("boss_gold_bonus_pct", 0) or 0)
                effective_gold = int(round(gold * (1 + _boss_pct / 100.0))) if _boss_pct else gold

                profile["gold"] = int(profile.get("gold", 0) or 0) + effective_gold
                profile["elixir"] = int(profile.get("elixir", 0) or 0) + elixir
                profile["dark_elixir"] = int(profile.get("dark_elixir", 0) or 0) + dark_elixir
                profile["gems"] = int(profile.get("gems", 0) or 0) + gems
                profile["raid_medals"] = int(profile.get("raid_medals", 0) or 0) + raid_medals
                profile["shiny_ore"] = int(profile.get("shiny_ore", 0) or 0) + shiny_ore
                profile["glowy_ore"] = int(profile.get("glowy_ore", 0) or 0) + glowy_ore
                profile["starry_ore"] = int(profile.get("starry_ore", 0) or 0) + starry_ore
                profile["clan_xp"] = int(profile.get("clan_xp", 0) or 0) + clan_xp
    
                profile.setdefault("town_hall", 1)
                profile.setdefault("stats", {})
                profile.setdefault("achievements", [])
    
                if gear_drop:
                    grant_equipment(profile, str(gear_drop))
    
                return state
    
            await update_mmo_state(ctx, _update)
    
            bonus_text = ""
    
            if reward.get("legend_chest"):
                bonus_text += " + **Legend Chest**"

            if gear_drop:
                gear_data = GEAR_CATALOG.get(str(gear_drop), {})
                gear_name = gear_data.get("name", str(gear_drop))
                gear_rarity = str(gear_data.get("rarity", "common")).title()
                bonus_text += f" + **Gear: {gear_name}** [{gear_rarity}]"
    
            reward_lines.append(
                f"<@{user_id}> — **{gold:,} Gold**, **{elixir:,} Elixir**, "
                f"**{dark_elixir:,} Dark Elixir**, **{gems} Gems**, "
                f"**{raid_medals} Raid Medals**, **{shiny_ore} Shiny Ore**, "
                f"**{glowy_ore} Glowy Ore**, **{starry_ore} Starry Ore**, "
                f"**{clan_xp} Clan XP**{bonus_text}"
            )
    
        return reward_lines

    @bot.tree.command(name="raidstatus", description="View the active raid boss, its HP, and player contributions")
    async def raidstatus(interaction: discord.Interaction):
        profiles = await _profiles()
        ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )

        town_hall = await _mmo_town_hall(
            str(interaction.user.id),
            interaction.user.display_name,
        )

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return

        # Read-only: do NOT spawn. Just report the current raid if one exists.
        data = await load_mmo_state(ctx)
        raids = data.setdefault("raids", {})
        raid = get_active_raid(raids)

        if not raid:
            await interaction.response.send_message(
                "💤 No raid boss is active right now. One will spawn automatically — watch the channel for the announcement!",
                ephemeral=True,
            )
            return

        health = int(raid.get("health", 0) or 0)
        max_health = int(raid.get("max_health", 0) or 0)
        pct = int((health / max_health) * 100) if max_health else 0
        phase = get_boss_phase(raid)

        # Build contribution leaderboard from raid["damage"]
        damage_map = raid.get("damage", {}) or {}
        total_damage = sum(int(v or 0) for v in damage_map.values())
        contrib_lines = []
        if damage_map:
            ranked = sorted(damage_map.items(), key=lambda kv: int(kv[1] or 0), reverse=True)
            for uid, dmg in ranked[:15]:
                dmg = int(dmg or 0)
                share = int((dmg / total_damage) * 100) if total_damage else 0
                contrib_lines.append(f"<@{uid}> — **{dmg:,}** dmg ({share}%)")
        else:
            contrib_lines.append("No attacks yet — be the first with `/bossattack`!")

        embed = discord.Embed(
            title=f"⚔️ {raid.get('boss_name', 'Raid Boss')}",
            color=0xE74C3C,
        )
        embed.add_field(
            name="Boss HP",
            value=f"**{health:,} / {max_health:,}** ({pct}%)",
            inline=False,
        )
        embed.add_field(name="Phase", value=str(phase), inline=True)
        embed.add_field(name="Raiders", value=str(len(raid.get("players", []))), inline=True)
        embed.add_field(name="Total Damage", value=f"{total_damage:,}", inline=True)
        embed.add_field(
            name="Player Contributions",
            value="\n".join(contrib_lines),
            inline=False,
        )
        embed.set_footer(text=f"Raid Entry Cost: {RAID_JOIN_COST} Raid Medals | Attack with /bossattack")

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="joinraid", description="Join the active raid boss")
    async def joinraid(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )

        town_hall = await _mmo_town_hall(
            str(interaction.user.id),
            interaction.user.display_name,
        )

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return

        current_raid_medals = int(profile.get("raid_medals", 0) or 0)

        if current_raid_medals < RAID_JOIN_COST:
            await interaction.response.send_message(
                f"❌ You need **{RAID_JOIN_COST} Raid Medals** to join raids.\n"
                f"You currently have **{current_raid_medals} Raid Medals**.",
                ephemeral=True,
            )
            return

        raid = await _get_active_raid()

        if not raid:
            await interaction.response.send_message(
                "💤 No raid boss is active right now. One will spawn automatically — watch the channel!",
                ephemeral=True,
            )
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            raids = state.setdefault("raids", {})
            active_raid = get_active_raid(raids)

            players = state.setdefault("players", {})
            player_profile = players.setdefault(str(interaction.user.id), {})

            if active_raid:
                if str(interaction.user.id) not in active_raid.get("players", []):
                    player_profile["raid_medals"] = max(
                        0,
                        int(player_profile.get("raid_medals", 0) or 0) - RAID_JOIN_COST,
                    )

                join_raid(active_raid, str(interaction.user.id))

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"You joined the raid for **{RAID_JOIN_COST} Raid Medals**."
        )

    @bot.tree.command(name="bossattack", description="Attack the active raid boss")
    async def bossattack(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )

        town_hall = await _mmo_town_hall(
            str(interaction.user.id),
            interaction.user.display_name,
        )

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return

        raid = await _get_active_raid()

        if not raid:
            await interaction.response.send_message(
                "💤 No raid boss is active right now. One will spawn automatically — watch the channel!",
                ephemeral=True,
            )
            return

        remaining = await _raid_attack_remaining(str(interaction.user.id), raid)

        if remaining > 0:
            minutes, seconds = divmod(remaining, 60)
            await interaction.response.send_message(
                f"⏳ Your army is recovering from the boss raid. Try `/bossattack` again in **{minutes}m {seconds}s**.",
                ephemeral=True,
            )
            return

        training_potion_available = await _has_boost_charge(
            str(interaction.user.id),
            "training_potion",
        )
    
        result = attack_raid_boss(
            raid,
            profile,
            training_potion_active=training_potion_available,
        )
    
        boost_text = ""
    
        await _stamp_raid_attack(
            str(interaction.user.id),
            interaction.user.display_name,
        )
    
        reward_lines = await _grant_defeat_rewards(result.get("defeat_rewards"))
    
        defeat_rewards = result.get("defeat_rewards") or {}
        player_reward = defeat_rewards.get(str(interaction.user.id), {})
        boosts_applied = player_reward.get("boosts_applied", []) if isinstance(player_reward, dict) else []
    
        if result.get("boss_defeated") and "training_potion" in boosts_applied:
            await _consume_boost_charge(
                str(interaction.user.id),
                "training_potion",
            )
    
            boost_text += (
                "\n\n🧪 Training Potion consumed."
                "\nBoss defeat rewards received:"
                "\n• +15% Gold"
                "\n• +15% Clan XP"
                "\n• +10% Elixir"
            )

        def _update(state_data):
            if not isinstance(state_data, dict):
                state_data = {}

            raids = state_data.setdefault("raids", {})

            if result.get("boss_defeated"):
                raids["active_raid"] = None
            else:
                raids["active_raid"] = raid

            return state_data

        await update_mmo_state(ctx, _update)

        title = "Boss Attack"

        description = format_attack_result(result) + boost_text

        if reward_lines:
            description += "\n\n🎁 **Boss Defeated — Rewards Paid**\n"
            description += "\n".join(reward_lines[:15])

        embed = discord.Embed(
            title=title,
            description=description,
            color=0xF39C12,
        )

        await interaction.response.send_message(embed=embed)
