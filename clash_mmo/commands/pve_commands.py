from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.gear_catalog import GEAR_CATALOG
from clash_mmo.game.equipment.service import grant_equipment
from clash_mmo.game.pve.chests import (
    CHEST_CONFIG,
    get_chest_name,
    roll_chest_rewards,
    roll_pve_chest_drop,
)
from clash_mmo.game.state import load_mmo_state, update_mmo_state


DAILY_COOLDOWN = 20 * 60 * 60
FARM_COOLDOWN = 3 * 60
TRAIN_COOLDOWN = 5 * 60
PVE_COOLDOWN = 10 * 60


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


def _pve_title_for_th(th: int) -> str:
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


def _roll_pve_attack(town_hall: int, active_hero_level: int = 1) -> dict:
    town_hall = max(1, int(town_hall or 1))
    active_hero_level = max(1, int(active_hero_level or 1))

    attack_power = town_hall + active_hero_level
    defense_roll = random.randint(4, 24)

    score = attack_power + random.randint(1, 20) - defense_roll

    if score < 2:
        stars = 0
    elif score < 8:
        stars = 1
    elif score < 14:
        stars = 2
    else:
        stars = 3

    stars = max(0, min(3, stars))

    base_gold = random.randint(120, 260) + town_hall * random.randint(35, 80)
    base_xp = random.randint(20, 45) + town_hall * random.randint(3, 8)

    if stars == 0:
        gold = max(25, int(base_gold * 0.25))
        clan_xp = max(5, int(base_xp * 0.25))
    elif stars == 1:
        gold = int(base_gold * 0.75)
        clan_xp = int(base_xp * 0.75)
    elif stars == 2:
        gold = int(base_gold * 1.15)
        clan_xp = int(base_xp * 1.10)
    else:
        gold = int(base_gold * 1.70)
        clan_xp = int(base_xp * 1.50)

    gems = 1 if stars == 3 and random.random() < 0.20 else 0
    medals = stars

    return {
        "stars": stars,
        "gold": gold,
        "clan_xp": clan_xp,
        "gems": gems,
        "raid_medals": medals,
        "attack_power": attack_power,
        "defense_roll": defense_roll,
    }


def register_pve_commands(bot, ctx):
    async def _profile(user: discord.Member | discord.User):
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

            profile.setdefault("town_hall", 1)
            profile.setdefault("gold", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("clan_xp", 0)
            profile.setdefault("daily_streak", 0)
            profile.setdefault("last_daily_key", None)
            profile.setdefault("cooldowns", {})
            profile.setdefault("stats", {})
            profile.setdefault("heroes", {})
            profile.setdefault("inventory", {})

            identity = profile.setdefault("identity", {})
            identity["display_name"] = display_name

            return state

        await update_mmo_state(ctx, _update)

        state = await load_mmo_state(ctx)
        return state.get("players", {}).get(user_id, {})

    async def _cooldown_remaining(user_id: str, key: str, cooldown_seconds: int) -> int:
        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(str(user_id), {})
        cooldowns = profile.get("cooldowns", {}) if isinstance(profile, dict) else {}

        last_used = int(cooldowns.get(key, 0) or 0)
        remaining = int(cooldown_seconds) - (_now() - last_used)

        return max(0, remaining)

    async def _stamp_cooldown(user_id: str, key: str, name: str = "Unknown"):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                str(user_id),
                name,
            )

            cooldowns = profile.setdefault("cooldowns", {})
            cooldowns[key] = _now()

            return state

        await update_mmo_state(ctx, _update)

    async def _grant_rewards(
        user: discord.Member | discord.User,
        *,
        gold: int = 0,
        gems: int = 0,
        raid_medals: int = 0,
        clan_xp: int = 0,
        stat_updates: dict | None = None,
        daily_streak: int | None = None,
        last_daily_key: str | None = None,
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
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + int(raid_medals))
            profile["clan_xp"] = max(0, int(profile.get("clan_xp", 0) or 0) + int(clan_xp))

            if daily_streak is not None:
                profile["daily_streak"] = max(0, int(daily_streak))

            if last_daily_key is not None:
                profile["last_daily_key"] = last_daily_key

            stats = profile.setdefault("stats", {})

            for key, delta in (stat_updates or {}).items():
                stats[key] = int(stats.get(key, 0) or 0) + int(delta)

            return state

        await update_mmo_state(ctx, _update)

    def _active_hero_level(profile: dict) -> int:
        active_hero = str(profile.get("active_hero") or "").strip().lower()
        heroes = profile.get("heroes", {})

        if not active_hero or not isinstance(heroes, dict):
            return 1

        hero_data = heroes.get(active_hero)

        if not isinstance(hero_data, dict):
            return 1

        return int(hero_data.get("level", 1) or 1)

    @bot.tree.command(name="daily", description="Claim your daily MMO rewards")
    async def daily(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        remaining = await _cooldown_remaining(
            str(interaction.user.id),
            "daily",
            DAILY_COOLDOWN,
        )

        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Daily rewards are cooling down. Try again in **{_fmt_remaining(remaining)}**.",
                ephemeral=True,
            )
            return

        town_hall = int(profile.get("town_hall", 1) or 1)
        today = _day_key()
        last_daily_key = profile.get("last_daily_key")
        current_streak = int(profile.get("daily_streak", 0) or 0)

        if last_daily_key == today:
            streak = current_streak
        else:
            streak = current_streak + 1

        gold = random.randint(350, 650) + town_hall * 75 + min(streak, 14) * 25
        clan_xp = random.randint(35, 75) + town_hall * 6
        gems = 1 if random.random() < 0.25 else 0
        raid_medals = 1 if random.random() < 0.20 else 0

        await _grant_rewards(
            interaction.user,
            gold=gold,
            gems=gems,
            raid_medals=raid_medals,
            clan_xp=clan_xp,
            daily_streak=streak,
            last_daily_key=today,
            stat_updates={"daily_claims": 1},
        )

        await _stamp_cooldown(
            str(interaction.user.id),
            "daily",
            interaction.user.display_name,
        )

        embed = discord.Embed(
            title="🎁 Daily Rewards Claimed",
            description=(
                f"Gold: **{gold:,}**\n"
                f"Clan XP: **{clan_xp:,}**\n"
                f"Gems: **{gems}**\n"
                f"Raid Medals: **{raid_medals}**\n"
                f"Daily Streak: **{streak} day(s)**"
            ),
            color=0x2ECC71,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="farm", description="Farm resources from nearby dead bases")
    async def farm(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        remaining = await _cooldown_remaining(
            str(interaction.user.id),
            "farm",
            FARM_COOLDOWN,
        )

        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Your builders are still collecting. Try again in **{_fmt_remaining(remaining)}**.",
                ephemeral=True,
            )
            return

        town_hall = int(profile.get("town_hall", 1) or 1)
        gold = random.randint(120, 350) + town_hall * random.randint(25, 55)
        clan_xp = random.randint(10, 35) + town_hall * 3

        await _grant_rewards(
            interaction.user,
            gold=gold,
            clan_xp=clan_xp,
            stat_updates={"farm_runs": 1},
        )

        await _stamp_cooldown(
            str(interaction.user.id),
            "farm",
            interaction.user.display_name,
        )

        await interaction.response.send_message(
            f"🌾 Farm complete! You earned **{gold:,} Gold** and **{clan_xp:,} Clan XP**."
        )

    @bot.tree.command(name="train", description="Train your army and gain MMO progress")
    async def train(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        remaining = await _cooldown_remaining(
            str(interaction.user.id),
            "train",
            TRAIN_COOLDOWN,
        )

        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Your army is still training. Try again in **{_fmt_remaining(remaining)}**.",
                ephemeral=True,
            )
            return

        town_hall = int(profile.get("town_hall", 1) or 1)
        active_hero = str(profile.get("active_hero") or "None").replace("_", " ").title()

        gold = random.randint(75, 200) + town_hall * 20
        clan_xp = random.randint(35, 90) + town_hall * 5

        await _grant_rewards(
            interaction.user,
            gold=gold,
            clan_xp=clan_xp,
            stat_updates={"training_sessions": 1},
        )

        await _stamp_cooldown(
            str(interaction.user.id),
            "train",
            interaction.user.display_name,
        )

        await interaction.response.send_message(
            f"⚔️ Training complete! Active Hero: **{active_hero}**\n"
            f"Rewards: **{gold:,} Gold**, **{clan_xp:,} Clan XP**"
        )

    @bot.tree.command(name="pve", description="Attack a random NPC village for loot and chest chances")
    async def pve(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        remaining = await _cooldown_remaining(
            str(interaction.user.id),
            "pve",
            PVE_COOLDOWN,
        )

        if remaining > 0:
            await interaction.response.send_message(
                f"⏳ Your army is recovering. Try again in **{_fmt_remaining(remaining)}**.",
                ephemeral=True,
            )
            return

        town_hall = int(profile.get("town_hall", 1) or 1)
        active_level = _active_hero_level(profile)
        result = _roll_pve_attack(town_hall, active_level)

        stars = int(result["stars"])
        chest_key = roll_pve_chest_drop(stars)
        chest_text = "No chest dropped."

        if chest_key:
            await ctx.add_shop_item(str(interaction.user.id), chest_key, 1)
            chest_text = f"Chest Drop: **{get_chest_name(chest_key)}**"

        await _grant_rewards(
            interaction.user,
            gold=int(result["gold"]),
            gems=int(result["gems"]),
            raid_medals=int(result["raid_medals"]),
            clan_xp=int(result["clan_xp"]),
            stat_updates={
                "pve_attacks": 1,
                "pve_stars": stars,
                "pve_triples": 1 if stars == 3 else 0,
                "pve_chests_found": 1 if chest_key else 0,
            },
        )

        await _stamp_cooldown(
            str(interaction.user.id),
            "pve",
            interaction.user.display_name,
        )

        star_text = "⭐" * stars if stars > 0 else "Failed Attack"

        embed = discord.Embed(
            title="🗡️ PvE Village Attack",
            description=(
                f"Result: **{star_text}**\n"
                f"Title: **{_pve_title_for_th(town_hall)}**\n\n"
                f"Gold: **{int(result['gold']):,}**\n"
                f"Clan XP: **{int(result['clan_xp']):,}**\n"
                f"Gems: **{int(result['gems'])}**\n"
                f"Raid Medals: **{int(result['raid_medals'])}**\n\n"
                f"{chest_text}"
            ),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="openchest", description="Open a chest from your inventory")
    @app_commands.describe(chest="Chest to open")
    async def openchest(interaction: discord.Interaction, chest: str):
        chest_key = str(chest or "").strip().lower()

        if chest_key not in CHEST_CONFIG:
            await interaction.response.send_message("❌ Invalid chest type.", ephemeral=True)
            return

        consumed = await ctx.consume_shop_item(str(interaction.user.id), chest_key)

        if not consumed:
            await interaction.response.send_message(
                f"❌ You do not have a **{get_chest_name(chest_key)}** to open.",
                ephemeral=True,
            )
            return

        profile = await _profile(interaction.user)
        active_hero = profile.get("active_hero")
        rewards = roll_chest_rewards(chest_key, active_hero)
        gear_drop = rewards.get("gear_drop")

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile_to_update = ensure_player_profile(
                state,
                str(interaction.user.id),
                interaction.user.display_name,
            )

            profile_to_update["gold"] = int(profile_to_update.get("gold", 0) or 0) + int(rewards.get("gold", 0) or 0)
            profile_to_update["gems"] = int(profile_to_update.get("gems", 0) or 0) + int(rewards.get("gems", 0) or 0)
            profile_to_update["raid_medals"] = int(profile_to_update.get("raid_medals", 0) or 0) + int(rewards.get("raid_medals", 0) or 0)
            profile_to_update["clan_xp"] = int(profile_to_update.get("clan_xp", 0) or 0) + int(rewards.get("clan_xp", 0) or 0)

            stats = profile_to_update.setdefault("stats", {})
            stats["chests_opened"] = int(stats.get("chests_opened", 0) or 0) + 1

            if gear_drop:
                grant_equipment(profile_to_update, str(gear_drop))

            return state

        await update_mmo_state(ctx, _update)

        lines = [
            f"💰 Gold: **{int(rewards['gold']):,}**",
            f"✨ Clan XP: **{int(rewards['clan_xp']):,}**",
            f"💎 Gems: **{int(rewards['gems'])}**",
            f"🎖️ Raid Medals: **{int(rewards['raid_medals'])}**",
        ]

        if gear_drop:
            gear_data = GEAR_CATALOG.get(str(gear_drop), {})
            gear_name = gear_data.get("name", str(gear_drop))
            gear_rarity = str(gear_data.get("rarity", "common")).title()
            lines.append(f"🛡️ Gear: **{gear_name}** [{gear_rarity}]")
        else:
            lines.append("🛡️ Gear: None")

        embed = discord.Embed(
            title=f"🎁 {rewards['chest_name']} Opened",
            description="\n".join(lines),
            color=0xF1C40F,
        )

        await interaction.response.send_message(embed=embed)

    @openchest.autocomplete("chest")
    async def openchest_autocomplete(interaction: discord.Interaction, current: str):
        current = str(current or "").lower()
        choices = []

        for chest_key, config in CHEST_CONFIG.items():
            name = str(config.get("name", chest_key))

            if current in chest_key.lower() or current in name.lower():
                choices.append(
                    app_commands.Choice(
                        name=f"{name} ({chest_key})",
                        value=chest_key,
                    )
                )

        return choices[:25]