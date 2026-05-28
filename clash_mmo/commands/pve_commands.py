from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import discord
from discord import app_commands

from clash_mmo.game.progression.costs import get_town_hall_upgrade_cost
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

    elixir = max(20, int(gold * random.uniform(0.25, 0.45)))
    dark_elixir = 0
    shiny_ore = 0
    glowy_ore = 0
    starry_ore = 0

    if stars >= 2 and random.random() < 0.06:
        dark_elixir = random.randint(15, 45)

    if stars == 3:
        if random.random() < 0.12:
            dark_elixir += random.randint(30, 90)
        if random.random() < 0.06:
            shiny_ore = random.randint(1, 2)
        if town_hall >= 10 and random.random() < 0.015:
            glowy_ore = 1

    return {
        "stars": stars,
        "gold": gold,
        "elixir": elixir,
        "dark_elixir": dark_elixir,
        "shiny_ore": shiny_ore,
        "glowy_ore": glowy_ore,
        "starry_ore": starry_ore,
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
            profile.setdefault("elixir", 0)
            profile.setdefault("dark_elixir", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("shiny_ore", 0)
            profile.setdefault("glowy_ore", 0)
            profile.setdefault("starry_ore", 0)
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
        elixir: int = 0,
        dark_elixir: int = 0,
        gems: int = 0,
        raid_medals: int = 0,
        shiny_ore: int = 0,
        glowy_ore: int = 0,
        starry_ore: int = 0,
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
            profile["elixir"] = max(0, int(profile.get("elixir", 0) or 0) + int(elixir))
            profile["dark_elixir"] = max(0, int(profile.get("dark_elixir", 0) or 0) + int(dark_elixir))
            profile["gems"] = max(0, int(profile.get("gems", 0) or 0) + int(gems))
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + int(raid_medals))
            profile["shiny_ore"] = max(0, int(profile.get("shiny_ore", 0) or 0) + int(shiny_ore))
            profile["glowy_ore"] = max(0, int(profile.get("glowy_ore", 0) or 0) + int(glowy_ore))
            profile["starry_ore"] = max(0, int(profile.get("starry_ore", 0) or 0) + int(starry_ore))
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


    async def _grant_mmo_inventory_item(user_id: str, item_id: str, quantity: int = 1):
        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(state, str(user_id), f"User {user_id}")
            inventory = profile.setdefault("inventory", {})
            items = inventory.setdefault("items", [])

            for item in items:
                if isinstance(item, dict) and str(item.get("item_id", "")).lower() == str(item_id).lower():
                    item["quantity"] = int(item.get("quantity", 1) or 1) + int(quantity)
                    return state

            items.append({
                "item_id": str(item_id),
                "quantity": int(quantity),
                "source": "pve_chest_drop",
            })
            return state

        await update_mmo_state(ctx, _update)

    async def _consume_mmo_inventory_item(user_id: str, item_id: str) -> bool:
        consumed = False

        def _update(state):
            nonlocal consumed

            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(state, str(user_id), f"User {user_id}")
            inventory = profile.setdefault("inventory", {})
            items = inventory.setdefault("items", [])

            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    continue

                if str(item.get("item_id") or "").strip().lower() != str(item_id).strip().lower():
                    continue

                quantity = int(item.get("quantity", 1) or 1)

                if quantity > 1:
                    item["quantity"] = quantity - 1
                else:
                    items.pop(index)

                consumed = True
                break

            return state

        await update_mmo_state(ctx, _update)
        return consumed

    def _roll_optional_resource(chance: float, low: int, high: int) -> int:
        if random.random() > float(chance):
            return 0
        return random.randint(int(low), int(high))

    def _active_hero_level(profile: dict) -> int:
        active_hero = str(profile.get("active_hero") or "").strip().lower()
        heroes = profile.get("heroes", {})

        if not active_hero or not isinstance(heroes, dict):
            return 1

        hero_data = heroes.get(active_hero)

        if not isinstance(hero_data, dict):
            return 1

        return int(hero_data.get("level", 1) or 1)
        
    @bot.tree.command(name="upgradecosts", description="View your next Town Hall upgrade cost")
    async def upgradecosts(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        current_th = int(profile.get("town_hall", 1) or 1)
        current_gold = int(profile.get("gold", 0) or 0)
        current_clan_xp = int(profile.get("clan_xp", 0) or 0)

        if current_th >= 16:
            await interaction.response.send_message("🏰 Your Town Hall is already maxed at **TH16**.")
            return

        cost = get_town_hall_upgrade_cost(current_th)

        gold_status = "✅" if current_gold >= cost["gold"] else "❌"
        xp_status = "✅" if current_clan_xp >= cost["clan_xp"] else "❌"

        embed = discord.Embed(
            title=f"🏰 TH{current_th} → TH{current_th + 1} Upgrade Cost",
            description=(
                f"{gold_status} Gold: **{current_gold:,} / {cost['gold']:,}**\n"
                f"{xp_status} Clan XP: **{current_clan_xp:,} / {cost['clan_xp']:,}**"
            ),
            color=0xF1C40F,
        )

        await interaction.response.send_message(embed=embed)
        
    @bot.tree.command(name="upgradehall", description="Upgrade your MMO Town Hall using Gold and Clan XP")
    async def upgradehall(interaction: discord.Interaction):
        profile = await _profile(interaction.user)

        current_th = int(profile.get("town_hall", 1) or 1)

        if current_th >= 16:
            await interaction.response.send_message(
                "🏰 Your Town Hall is already maxed at **TH16**.",
                ephemeral=True,
            )
            return

        cost = get_town_hall_upgrade_cost(current_th)

        current_gold = int(profile.get("gold", 0) or 0)
        current_clan_xp = int(profile.get("clan_xp", 0) or 0)

        if current_gold < cost["gold"] or current_clan_xp < cost["clan_xp"]:
            await interaction.response.send_message(
                f"❌ Upgrading to **TH{current_th + 1}** requires "
                f"**{cost['gold']:,} Gold** and **{cost['clan_xp']:,} Clan XP**.\n"
                f"You have **{current_gold:,} Gold** and **{current_clan_xp:,} Clan XP**.",
                ephemeral=True,
            )
            return

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile_to_update = ensure_player_profile(
                state,
                str(interaction.user.id),
                interaction.user.display_name,
            )

            profile_to_update["gold"] = max(
                0,
                int(profile_to_update.get("gold", 0) or 0) - int(cost["gold"]),
            )
            profile_to_update["clan_xp"] = max(
                0,
                int(profile_to_update.get("clan_xp", 0) or 0) - int(cost["clan_xp"]),
            )
            profile_to_update["town_hall"] = current_th + 1

            stats = profile_to_update.setdefault("stats", {})
            stats["town_hall_upgrades"] = int(stats.get("town_hall_upgrades", 0) or 0) + 1

            return state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"🏰 Town Hall upgraded to **TH{current_th + 1}**!\n"
            f"Cost: **{cost['gold']:,} Gold** + **{cost['clan_xp']:,} Clan XP**"
        )

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

        gold = random.randint(250, 500) + town_hall * 55 + min(streak, 14) * 20
        elixir = random.randint(60, 180) + town_hall * 18
        clan_xp = random.randint(25, 60) + town_hall * 5
        gems = 1 if random.random() < 0.25 else 0
        raid_medals = 1 if random.random() < 0.20 else 0
        dark_elixir = _roll_optional_resource(0.02 + min(town_hall, 16) * 0.005, 10, 25 + town_hall * 4)
        shiny_ore = _roll_optional_resource(0.01 if town_hall < 8 else 0.04, 1, 2)
        glowy_ore = _roll_optional_resource(0.01 if town_hall >= 10 else 0.0, 1, 1)
        starry_ore = 0

        await _grant_rewards(
            interaction.user,
            gold=gold,
            elixir=elixir,
            dark_elixir=dark_elixir,
            gems=gems,
            raid_medals=raid_medals,
            shiny_ore=shiny_ore,
            glowy_ore=glowy_ore,
            starry_ore=starry_ore,
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
                f"Elixir: **{elixir:,}**\n"
                f"Clan XP: **{clan_xp:,}**\n"
                f"Gems: **{gems}**\n"
                f"Raid Medals: **{raid_medals}**\n"
                f"Dark Elixir: **{dark_elixir:,}**\n"
                f"Shiny Ore: **{shiny_ore}**\n"
                f"Glowy Ore: **{glowy_ore}**\n"
                f"Starry Ore: **{starry_ore}**\n"
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
        gold = random.randint(90, 240) + town_hall * random.randint(18, 42)
        elixir = random.randint(45, 130) + town_hall * random.randint(8, 22)
        clan_xp = random.randint(8, 25) + town_hall * 2
        dark_elixir = _roll_optional_resource(0.01 + min(town_hall, 16) * 0.003, 5, 15 + town_hall * 2)
        shiny_ore = _roll_optional_resource(0.02 if town_hall >= 8 else 0.0, 1, 1)

        await _grant_rewards(
            interaction.user,
            gold=gold,
            elixir=elixir,
            dark_elixir=dark_elixir,
            shiny_ore=shiny_ore,
            clan_xp=clan_xp,
            stat_updates={"farm_runs": 1},
        )

        await _stamp_cooldown(
            str(interaction.user.id),
            "farm",
            interaction.user.display_name,
        )

        await interaction.response.send_message(
            f"🌾 Farm complete! You earned **{gold:,} Gold**, **{elixir:,} Elixir**, "
            f"**{clan_xp:,} Clan XP**, **{dark_elixir:,} Dark Elixir**, and **{shiny_ore} Shiny Ore**."
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

        gold = random.randint(50, 150) + town_hall * 14
        elixir = random.randint(75, 200) + town_hall * 18
        clan_xp = random.randint(30, 75) + town_hall * 4
        dark_elixir = _roll_optional_resource(0.01 if town_hall >= 7 else 0.0, 10, 25 + town_hall * 2)

        await _grant_rewards(
            interaction.user,
            gold=gold,
            elixir=elixir,
            dark_elixir=dark_elixir,
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
            f"Rewards: **{gold:,} Gold**, **{elixir:,} Elixir**, "
            f"**{clan_xp:,} Clan XP**, **{dark_elixir:,} Dark Elixir**"
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
            await _grant_mmo_inventory_item(str(interaction.user.id), chest_key, 1)
            chest_text = f"Chest Drop: **{get_chest_name(chest_key)}**"

        await _grant_rewards(
            interaction.user,
            gold=int(result["gold"]),
            elixir=int(result["elixir"]),
            dark_elixir=int(result["dark_elixir"]),
            gems=int(result["gems"]),
            raid_medals=int(result["raid_medals"]),
            shiny_ore=int(result["shiny_ore"]),
            glowy_ore=int(result["glowy_ore"]),
            starry_ore=int(result["starry_ore"]),
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
                f"Elixir: **{int(result['elixir']):,}**\n"
                f"Clan XP: **{int(result['clan_xp']):,}**\n"
                f"Gems: **{int(result['gems'])}**\n"
                f"Raid Medals: **{int(result['raid_medals'])}**\n"
                f"Dark Elixir: **{int(result['dark_elixir']):,}**\n"
                f"Shiny Ore: **{int(result['shiny_ore'])}**\n"
                f"Glowy Ore: **{int(result['glowy_ore'])}**\n"
                f"Starry Ore: **{int(result['starry_ore'])}**\n\n"
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

        consumed = await _consume_mmo_inventory_item(str(interaction.user.id), chest_key)

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
            profile_to_update["elixir"] = int(profile_to_update.get("elixir", 0) or 0) + int(rewards.get("elixir", 0) or 0)
            profile_to_update["dark_elixir"] = int(profile_to_update.get("dark_elixir", 0) or 0) + int(rewards.get("dark_elixir", 0) or 0)
            profile_to_update["gems"] = int(profile_to_update.get("gems", 0) or 0) + int(rewards.get("gems", 0) or 0)
            profile_to_update["raid_medals"] = int(profile_to_update.get("raid_medals", 0) or 0) + int(rewards.get("raid_medals", 0) or 0)
            profile_to_update["shiny_ore"] = int(profile_to_update.get("shiny_ore", 0) or 0) + int(rewards.get("shiny_ore", 0) or 0)
            profile_to_update["glowy_ore"] = int(profile_to_update.get("glowy_ore", 0) or 0) + int(rewards.get("glowy_ore", 0) or 0)
            profile_to_update["starry_ore"] = int(profile_to_update.get("starry_ore", 0) or 0) + int(rewards.get("starry_ore", 0) or 0)
            profile_to_update["clan_xp"] = int(profile_to_update.get("clan_xp", 0) or 0) + int(rewards.get("clan_xp", 0) or 0)

            stats = profile_to_update.setdefault("stats", {})
            stats["chests_opened"] = int(stats.get("chests_opened", 0) or 0) + 1

            if gear_drop:
                grant_equipment(profile_to_update, str(gear_drop))

            return state

        await update_mmo_state(ctx, _update)

        lines = [
            f"💰 Gold: **{int(rewards['gold']):,}**",
            f"🧪 Elixir: **{int(rewards.get('elixir', 0)):,}**",
            f"✨ Clan XP: **{int(rewards['clan_xp']):,}**",
            f"💎 Gems: **{int(rewards['gems'])}**",
            f"🎖️ Raid Medals: **{int(rewards['raid_medals'])}**",
            f"🟣 Dark Elixir: **{int(rewards.get('dark_elixir', 0)):,}**",
            f"🔹 Shiny Ore: **{int(rewards.get('shiny_ore', 0))}**",
            f"🔷 Glowy Ore: **{int(rewards.get('glowy_ore', 0))}**",
            f"🌟 Starry Ore: **{int(rewards.get('starry_ore', 0))}**",
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