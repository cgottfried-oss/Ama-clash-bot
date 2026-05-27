from __future__ import annotations

import random

import discord

RAID_UNLOCK_TH = 7
RAID_ATTACK_COOLDOWN_SECONDS = 10 * 60

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.service import grant_equipment
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.pve import (
    RAID_BOSSES,
    attack_raid_boss,
    format_attack_result,
    format_raid_status,
    get_active_raid,
    join_raid,
    start_raid,
)

from clash_mmo.game.state import (
    load_mmo_state,
    update_mmo_state,
)


def register_raid_commands(bot, ctx):
    add_shop_item = ctx.add_shop_item

    async def _profiles():
        data = await load_mmo_state(ctx)
        data.setdefault("players", {})
        return data
        
    async def _raid_attack_remaining(user_id: str, raid: dict) -> int:
        stored = await ctx.load_coins()
        entry = stored.get("users", {}).get(str(user_id), {})
        cooldowns = entry.get("cooldowns", {}) if isinstance(entry, dict) else {}

        last_attack = int(cooldowns.get("attackraid", 0) or 0)

        mechanics = raid.get("mechanics", {}) if isinstance(raid, dict) else {}
        user_mechanics = mechanics.get(str(user_id), {}) if isinstance(mechanics, dict) else {}
        penalty = int(user_mechanics.get("cooldown_penalty_seconds", 0) or 0)

        cooldown_seconds = RAID_ATTACK_COOLDOWN_SECONDS + penalty
        remaining = cooldown_seconds - (int(ctx.time.time()) - last_attack)

        return max(0, remaining)


    async def _stamp_raid_attack(user_id: str):
        def _update(data):
            if not isinstance(data, dict):
                data = {}

            users = data.setdefault("users", {})
            entry = users.setdefault(str(user_id), {})
            cooldowns = entry.setdefault("cooldowns", {})
            cooldowns["attackraid"] = int(ctx.time.time())

            return data

        await ctx.update_json_file(ctx.COINS_FILE, _update)
        
    async def _economy_town_hall(user_id: str) -> int:
        stored = await ctx.load_coins()
        entry = stored.get("users", {}).get(str(user_id), {})
        return int(entry.get("town_hall", 1) or 1)

    def _pick_random_boss_id() -> str:
        return random.choice(list(RAID_BOSSES.keys()))

    async def _ensure_active_raid():
        spawned = False
        spawned_boss = None

        def _update(state):
            nonlocal spawned, spawned_boss

            if not isinstance(state, dict):
                state = {}

            raids = state.setdefault("raids", {})
            raid = get_active_raid(raids)

            if not raid:
                boss_id = _pick_random_boss_id()
                spawned_boss = start_raid(raids, boss_id)
                spawned = True

            return state

        await update_mmo_state(ctx, _update)

        data = await load_mmo_state(ctx)
        raids = data.setdefault("raids", {})
        return get_active_raid(raids), spawned, spawned_boss

    async def _grant_defeat_rewards(defeat_rewards: dict | None):
        if not defeat_rewards:
            return []

        reward_lines = []

        for user_id, reward in defeat_rewards.items():
            gold = int(reward.get("gold", 0) or 0)
            gems = int(reward.get("gems", 0) or 0)
            medals = int(reward.get("medals", 0) or 0)
            clan_xp = int(reward.get("clan_xp", 0) or 0)

            def _update(data):
                if not isinstance(data, dict):
                    data = {}

                users = data.setdefault("users", {})
                entry = users.setdefault(str(user_id), {
                    "balance": 0,
                    "lifetime_earned": 0,
                    "name": "Unknown",
                })

                entry["balance"] = int(entry.get("balance", 0) or 0) + gold
                entry["lifetime_earned"] = int(entry.get("lifetime_earned", 0) or 0) + gold
                entry["gems"] = int(entry.get("gems", 0) or 0) + gems
                entry["raid_medals"] = int(entry.get("raid_medals", 0) or 0) + medals
                entry["clan_xp"] = int(entry.get("clan_xp", 0) or 0) + clan_xp
                entry.setdefault("town_hall", 1)
                entry.setdefault("stats", {})
                entry.setdefault("achievements", [])

                return data

            await ctx.update_json_file(ctx.COINS_FILE, _update)

            bonus_text = ""

            if reward.get("legend_chest"):
                await add_shop_item(str(user_id), "legend_chest", 1)
                bonus_text += " + **Legend Chest**"

            gear_drop = reward.get("gear_drop")
            if gear_drop:
                def _gear_update(state):
                    if not isinstance(state, dict):
                        state = {}

                    players = state.setdefault("players", {})
                    profile = ensure_player_profile(
                        state,
                        str(user_id),
                        f"User {user_id}",
                    )

                    grant_equipment(profile, str(gear_drop))
                    return state

                await update_mmo_state(ctx, _gear_update)
                gear_name = GEAR_CATALOG.get(str(gear_drop), {}).get("name", str(gear_drop))
                bonus_text += f" + **Gear: {gear_drop}**"

            reward_lines.append(
                f"<@{user_id}> — **{gold:,} Gold**, **{gems} Gems**, "
                f"**{medals} Medals**, **{clan_xp} Clan XP**{bonus_text}"
            )

        return reward_lines

    @bot.tree.command(name="raidstatus", description="View the current auto-spawned MMO raid boss")
    async def raidstatus(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )
        
        town_hall = await _economy_town_hall(str(interaction.user.id))

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return
            
        raid, spawned, spawned_boss = await _ensure_active_raid()
        
        if not raid:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return

        title = "PvE Raid"
        if spawned and spawned_boss:
            title = f"⚠️ New Raid Boss Spawned: {spawned_boss.get('boss_name', 'Unknown Boss')}"

        embed = discord.Embed(
            title=title,
            description=format_raid_status(raid),
            color=0xE74C3C,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="joinraid", description="Join the active auto-spawned MMO raid")
    async def joinraid(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )
        
        town_hall = await _economy_town_hall(str(interaction.user.id))

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return
        
        raid, spawned, spawned_boss = await _ensure_active_raid()
        
        if not raid:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            raids = state.setdefault("raids", {})
            active_raid = get_active_raid(raids)

            if active_raid:
                join_raid(active_raid, str(interaction.user.id))

            return state

        await update_mmo_state(ctx, _update)

        spawn_text = ""
        if spawned and spawned_boss:
            spawn_text = f"⚠️ A new raid boss spawned: **{spawned_boss.get('boss_name', 'Unknown Boss')}**\n"

        await interaction.response.send_message(f"{spawn_text}You joined the raid.")

    @bot.tree.command(name="attackraid", description="Attack the active auto-spawned MMO raid boss")
    async def attackraid(interaction: discord.Interaction):
        profiles = await _profiles()
        profile = ensure_player_profile(
            profiles,
            str(interaction.user.id),
            interaction.user.display_name,
        )
        
        town_hall = await _economy_town_hall(str(interaction.user.id))

        if town_hall < RAID_UNLOCK_TH:
            await interaction.response.send_message(
                "⚔️ MMO Raid Bosses unlock at **Town Hall 7**.",
                ephemeral=True,
            )
            return

        raid, spawned, spawned_boss = await _ensure_active_raid()

        if not raid:
            await interaction.response.send_message("No active raid.", ephemeral=True)
            return
            
        remaining = await _raid_attack_remaining(str(interaction.user.id), raid)

        if remaining > 0:
            minutes, seconds = divmod(remaining, 60)
            await interaction.response.send_message(
                f"⏳ Your army is recovering from the raid. Try again in **{minutes}m {seconds}s**.",
                ephemeral=True,
            )
            return

        result = attack_raid_boss(raid, profile)
        await _stamp_raid_attack(str(interaction.user.id))
        reward_lines = await _grant_defeat_rewards(result.get("defeat_rewards"))

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

        title = "Raid Attack"
        if spawned and spawned_boss:
            title = f"⚠️ New Raid Boss Spawned: {spawned_boss.get('boss_name', 'Unknown Boss')}"

        description = format_attack_result(result)

        if reward_lines:
            description += "\n\n🎁 **Boss Defeated — Rewards Paid**\n"
            description += "\n".join(reward_lines[:15])

        embed = discord.Embed(
            title=title,
            description=description,
            color=0xF39C12,
        )

        await interaction.response.send_message(embed=embed)