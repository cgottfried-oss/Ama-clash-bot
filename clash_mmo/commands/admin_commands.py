from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands

from clash_mmo.game.core.profiles import ensure_player_profile
from clash_mmo.game.equipment.service import normalize_hero_loadouts, unlock_hero
from clash_mmo.game.state import load_mmo_state, update_mmo_state


def register_admin_commands(bot, ctx):
    load_coins = ctx.load_coins
    SHOP_ITEMS = ctx.SHOP_ITEMS
    
    def _unlock_heroes_for_town_hall(profile: dict, town_hall: int):
        unlocked = []

        hero_unlocks = [
            (3, "king"),
            (5, "queen"),
            (7, "warden"),
            (10, "royal_champion"),
        ]

        for required_th, hero_id in hero_unlocks:
            if town_hall >= required_th:
                unlock_hero(profile, hero_id)
                unlocked.append(hero_id)

        heroes = normalize_hero_loadouts(profile)

        if unlocked and not profile.get("active_hero"):
            profile["active_hero"] = unlocked[0]

        if profile.get("active_hero") not in heroes and unlocked:
            profile["active_hero"] = unlocked[0]

        return unlocked

    def _is_owner(interaction: discord.Interaction) -> bool:
        return int(interaction.user.id) == int(getattr(ctx, "MMO_OWNER_ID", 0) or 0)

    async def _ensure_user(user: discord.abc.User, display_name: str | None = None):
        user_id = str(user.id)
        name = display_name or getattr(user, "display_name", None) or getattr(user, "name", "Unknown")

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}

            users = stored.setdefault("users", {})
            stored.setdefault("processed_wars", [])
            stored.setdefault("processed_clutches", [])
            stored.setdefault("advisor_claims", {})

            entry = users.setdefault(
                user_id,
                {
                    "balance": 0,
                    "lifetime_earned": 0,
                    "name": name,
                },
            )

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

            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)

    @bot.tree.command(name="adminview", description="Owner: privately view a member's MMO profile and inventory")
    @app_commands.describe(member="Member to inspect")
    async def adminview(interaction: discord.Interaction, member: discord.Member):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        user_id = str(member.id)
        display_name = getattr(member, "display_name", member.name)

        # Ensure MMO profile exists.
        def _ensure_mmo_profile(state):
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
            profile.setdefault("cooldowns", {})
            profile.setdefault("boosts", {})
            profile.setdefault("stats", {})
            profile.setdefault("achievements", [])
            profile.setdefault("inventory", {})
            profile.setdefault("heroes", {})

            identity = profile.setdefault("identity", {})
            identity["display_name"] = display_name

            return state

        await update_mmo_state(ctx, _ensure_mmo_profile)

        state = await load_mmo_state(ctx)
        profile = state.get("players", {}).get(user_id, {})

        shop_data = await ctx.load_shop_data()
        shop_inventory = (
            shop_data.get("users", {})
            .get(user_id, {})
            .get("inventory", {})
        )

        profile_inventory = profile.get("inventory", {})
        if not isinstance(profile_inventory, dict):
            profile_inventory = {}

        owned_gear = profile_inventory.get("items", [])
        if not isinstance(owned_gear, list):
            owned_gear = []

        cooldowns = profile.get("cooldowns", {})
        if not isinstance(cooldowns, dict):
            cooldowns = {}

        boosts = profile.get("boosts", {})
        if not isinstance(boosts, dict):
            boosts = {}

        stats = profile.get("stats", {})
        if not isinstance(stats, dict):
            stats = {}

        achievements = profile.get("achievements", [])
        if not isinstance(achievements, list):
            achievements = []

        heroes = profile.get("heroes", {})
        if not isinstance(heroes, dict):
            heroes = {}

        shop_inventory_lines = []

        for item_key, qty in sorted(shop_inventory.items()):
            item_name = SHOP_ITEMS.get(item_key, {}).get("name", item_key)
            shop_inventory_lines.append(f"**{item_name}** (`{item_key}`): x{int(qty or 0)}")

        if not shop_inventory_lines:
            shop_inventory_lines = ["No shop/chest inventory items."]

        gear_lines = []

        grouped_gear = {}

        for item in owned_gear:
            if not isinstance(item, dict):
                continue

            item_id = str(item.get("item_id", "unknown"))
            grouped_gear.setdefault(
                item_id,
                {
                    "count": 0,
                    "slot": item.get("slot", "unknown"),
                    "rarity": item.get("rarity", "common"),
                },
            )
            grouped_gear[item_id]["count"] += 1

        for item_id, data in sorted(grouped_gear.items()):
            gear_lines.append(
                f"**{item_id}** — {str(data['rarity']).title()} {str(data['slot']).title()} x{data['count']}"
            )

        if not gear_lines:
            gear_lines = ["No MMO gear owned."]

        cooldown_lines = []

        for key, value in sorted(cooldowns.items()):
            try:
                timestamp = int(value or 0)
                cooldown_lines.append(
                    f"`{key}`: {discord.utils.format_dt(datetime.fromtimestamp(timestamp), style='R')}"
                )
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

        hero_lines = []

        for hero_id, hero_data in sorted(heroes.items()):
            if not isinstance(hero_data, dict):
                hero_lines.append(f"**{hero_id}** — legacy value: `{hero_data}`")
                continue

            level = int(hero_data.get("level", 1) or 1)
            equipped_ability = hero_data.get("equipped_ability") or "None"
            equipment = hero_data.get("equipment", {})
            equipment_count = len(equipment) if isinstance(equipment, dict) else 0

            active_marker = " ⭐" if profile.get("active_hero") == hero_id else ""

            hero_lines.append(
                f"**{hero_id.replace('_', ' ').title()}**{active_marker} — "
                f"Lv {level}, Ability: `{equipped_ability}`, Gear Equipped: {equipment_count}"
            )

        if not hero_lines:
            hero_lines = ["No heroes unlocked."]

        embed = discord.Embed(
            title=f"🛠️ Admin MMO View: {member.display_name}",
            color=0xE67E22,
        )

        embed.add_field(
            name="Account",
            value=(
                f"Gold: **{int(profile.get('gold', 0) or 0):,}**\n"
                f"Clan XP: **{int(profile.get('clan_xp', 0) or 0):,}**\n"
                f"Town Hall: **TH{int(profile.get('town_hall', 1) or 1)}**\n"
                f"Gems: **{int(profile.get('gems', 0) or 0):,}**\n"
                f"Raid Medals: **{int(profile.get('raid_medals', 0) or 0):,}**\n"
                f"Daily Streak: **{int(profile.get('daily_streak', 0) or 0)}**\n"
                f"Active Hero: **{str(profile.get('active_hero') or 'None').replace('_', ' ').title()}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="Heroes",
            value="\n".join(hero_lines[:10]),
            inline=False,
        )

        embed.add_field(
            name="MMO Gear",
            value="\n".join(gear_lines[:15]),
            inline=False,
        )

        embed.add_field(
            name="Shop / Chest Inventory",
            value="\n".join(shop_inventory_lines[:20]),
            inline=False,
        )

        embed.add_field(
            name="Boosts",
            value="\n".join(boost_lines[:10]),
            inline=False,
        )

        embed.add_field(
            name="Cooldowns",
            value="\n".join(cooldown_lines[:10]),
            inline=False,
        )

        embed.add_field(
            name="Stats",
            value="\n".join(stat_lines[:15]),
            inline=False,
        )

        embed.add_field(
            name="Achievements",
            value=f"{len(achievements)} unlocked",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="adminset", description="Owner: set a member's MMO profile values")
    @app_commands.describe(
        member="Member to adjust",
        gold="Set current Gold balance",
        clan_xp="Set Clan XP",
        gems="Set Gems",
        medals="Set Raid Medals",
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
        town_hall: int | None = None,
        reason: str = "Manual admin adjustment",
    ):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        user_id = str(member.id)
        name = getattr(member, "display_name", member.name)

        changes = []
        unlocked_heroes = []

        def _update(state):
            nonlocal unlocked_heroes

            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(
                state,
                user_id,
                name,
            )

            profile.setdefault("gold", 0)
            profile.setdefault("gems", 0)
            profile.setdefault("raid_medals", 0)
            profile.setdefault("clan_xp", 0)
            profile.setdefault("town_hall", 1)
            profile.setdefault("daily_streak", 0)
            profile.setdefault("cooldowns", {})
            profile.setdefault("stats", {})
            profile.setdefault("inventory", {})
            profile.setdefault("heroes", {})

            if gold is not None:
                profile["gold"] = max(0, int(gold))
                changes.append(f"Gold → **{profile['gold']:,}**")

            if clan_xp is not None:
                profile["clan_xp"] = max(0, int(clan_xp))
                changes.append(f"Clan XP → **{profile['clan_xp']:,}**")

            if gems is not None:
                profile["gems"] = max(0, int(gems))
                changes.append(f"Gems → **{profile['gems']:,}**")

            if medals is not None:
                profile["raid_medals"] = max(0, int(medals))
                changes.append(f"Raid Medals → **{profile['raid_medals']:,}**")

            if town_hall is not None:
                profile["town_hall"] = max(1, min(16, int(town_hall)))
                changes.append(f"Town Hall → **TH{profile['town_hall']}**")
                unlocked_heroes = _unlock_heroes_for_town_hall(
                    profile,
                    int(profile["town_hall"]),
                )

            identity = profile.setdefault("identity", {})
            identity["display_name"] = name

            return state

        await update_mmo_state(ctx, _update)

        if not changes:
            await interaction.response.send_message(
                "ℹ️ No values were changed. Add at least one field like `gold`, `clan_xp`, or `town_hall`.",
                ephemeral=True,
            )
            return

        hero_text = ""

        if unlocked_heroes:
            hero_names = ", ".join(
                hero_id.replace("_", " ").title()
                for hero_id in unlocked_heroes
            )
            hero_text = f"\nUnlocked Heroes → **{hero_names}**"

        await interaction.response.send_message(
            f"✅ Updated MMO profile for {member.mention}\n"
            + "\n".join(changes)
            + hero_text
            + f"\nReason: {reason}",
            ephemeral=True,
        )

    @bot.tree.command(name="adminreset", description="Owner: wipe a player's Clash MMO data")
    @app_commands.describe(
        user="Discord user whose MMO data should be wiped",
        wipe_economy="Also wipe coins, gems, medals, chests, shop inventory, cooldowns, and TH progress",
        wipe_mmo="Wipe MMO profile, heroes, gear, PvP, raid participation, and MMO state profile",
    )
    async def adminreset(
        interaction: discord.Interaction,
        user: discord.User,
        wipe_economy: bool = True,
        wipe_mmo: bool = True,
    ):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        target_id = str(user.id)
        wiped = []

        if wipe_economy:
            def _wipe_coins(data):
                if not isinstance(data, dict):
                    data = {}

                users = data.setdefault("users", {})
                users.pop(target_id, None)

                return data

            await ctx.update_json_file(ctx.COINS_FILE, _wipe_coins)

            def _wipe_shop(data):
                if not isinstance(data, dict):
                    data = {}

                users = data.setdefault("users", {})
                users.pop(target_id, None)

                return data

            await ctx.update_json_file(ctx.SHOP_FILE, _wipe_shop)
            wiped.append("economy/shop")

        if wipe_mmo:
            def _wipe_mmo(state):
                if not isinstance(state, dict):
                    state = {}

                players = state.setdefault("players", {})
                players.pop(target_id, None)

                raids = state.setdefault("raids", {})
                active_raid = raids.get("active_raid")

                if isinstance(active_raid, dict):
                    players_list = active_raid.get("players", [])
                    if isinstance(players_list, list):
                        active_raid["players"] = [
                            player_id for player_id in players_list
                            if str(player_id) != target_id
                        ]

                    damage = active_raid.get("damage", {})
                    if isinstance(damage, dict):
                        damage.pop(target_id, None)

                    mechanics = active_raid.get("mechanics", {})
                    if isinstance(mechanics, dict):
                        mechanics.pop(target_id, None)

                return state

            await update_mmo_state(ctx, _wipe_mmo)
            wiped.append("mmo")

        if not wiped:
            await interaction.response.send_message(
                "Nothing was wiped. Choose at least one wipe option.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Wiped **{', '.join(wiped)}** data for {user.mention}.",
            ephemeral=True,
        )
        
    @bot.tree.command(name="adminclearcooldowns", description="Owner: clear all of your Clash MMO cooldowns")
    async def adminclearcooldowns(interaction: discord.Interaction):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        user_id = str(interaction.user.id)

        # Clear economy cooldowns: /daily, /farm, /raid, /train, /attackraid, etc.
        def _clear_coin_cooldowns(data):
            if not isinstance(data, dict):
                data = {}

            users = data.setdefault("users", {})
            entry = users.setdefault(user_id, {})
            entry["cooldowns"] = {}

            return data

        await ctx.update_json_file(ctx.COINS_FILE, _clear_coin_cooldowns)

        # Clear MMO profile cooldowns: /lootgear and future MMO-only cooldowns.
        def _clear_mmo_cooldowns(state):
            if not isinstance(state, dict):
                state = {}

            players = state.setdefault("players", {})
            profile = players.get(user_id)

            if isinstance(profile, dict):
                profile["cooldowns"] = {}

            raids = state.setdefault("raids", {})
            active_raid = raids.get("active_raid")

            if isinstance(active_raid, dict):
                mechanics = active_raid.get("mechanics", {})
                if isinstance(mechanics, dict):
                    mechanics.pop(user_id, None)

            return state

        await update_mmo_state(ctx, _clear_mmo_cooldowns)

        await interaction.response.send_message(
            "✅ Your economy, MMO, gear, raid, and boss mechanic cooldowns were cleared.",
            ephemeral=True,
        )