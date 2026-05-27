from __future__ import annotations

from datetime import datetime

import discord
from discord import app_commands

from clash_mmo.game.state import update_mmo_state


def register_admin_commands(bot, ctx):
    load_coins = ctx.load_coins
    SHOP_ITEMS = ctx.SHOP_ITEMS

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

    @bot.tree.command(name="adminview", description="Owner: privately view a member's economy account and inventory")
    @app_commands.describe(member="Member to inspect")
    async def adminview(interaction: discord.Interaction, member: discord.Member):
        if not _is_owner(interaction):
            await interaction.response.send_message("❌ Owner only.", ephemeral=True)
            return

        await _ensure_user(member, member.display_name)

        stored = await load_coins()
        user_entry = stored.get("users", {}).get(str(member.id), {})

        shop_data = await ctx.load_shop_data()
        inventory = (
            shop_data.get("users", {})
            .get(str(member.id), {})
            .get("inventory", {})
        )

        cooldowns = user_entry.get("cooldowns", {}) if isinstance(user_entry.get("cooldowns", {}), dict) else {}
        boosts = user_entry.get("boosts", {}) if isinstance(user_entry.get("boosts", {}), dict) else {}
        stats = user_entry.get("stats", {}) if isinstance(user_entry.get("stats", {}), dict) else {}

        inventory_lines = []
        for item_key, qty in sorted(inventory.items()):
            item_name = SHOP_ITEMS.get(item_key, {}).get("name", item_key)
            inventory_lines.append(f"**{item_name}** (`{item_key}`): x{int(qty or 0)}")

        if not inventory_lines:
            inventory_lines = ["No inventory items."]

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

        embed = discord.Embed(
            title=f"🛠️ Admin Economy View: {member.display_name}",
            color=0xE67E22,
        )

        embed.add_field(
            name="Account",
            value=(
                f"Gold: **{int(user_entry.get('balance', 0) or 0):,}**\n"
                f"Lifetime Earned: **{int(user_entry.get('lifetime_earned', 0) or 0):,}**\n"
                f"Clan XP: **{int(user_entry.get('clan_xp', 0) or 0):,}**\n"
                f"Town Hall: **{int(user_entry.get('town_hall', 1) or 1)}**\n"
                f"Gems: **{int(user_entry.get('gems', 0) or 0):,}**\n"
                f"Raid Medals: **{int(user_entry.get('raid_medals', 0) or 0):,}**\n"
            ),
            inline=False,
        )

        embed.add_field(name="Inventory", value="\n".join(inventory_lines[:20]), inline=False)
        embed.add_field(name="Boosts", value="\n".join(boost_lines[:10]), inline=False)
        embed.add_field(name="Cooldowns", value="\n".join(cooldown_lines[:10]), inline=False)
        embed.add_field(name="Stats", value="\n".join(stat_lines[:15]), inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="adminset", description="Owner: set a member's economy account values")
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

        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}

            users = stored.setdefault("users", {})
            entry = users.setdefault(
                user_id,
                {
                    "balance": 0,
                    "lifetime_earned": 0,
                    "name": name,
                },
            )

            entry.setdefault("gems", 0)
            entry.setdefault("raid_medals", 0)
            entry.setdefault("clan_xp", 0)
            entry.setdefault("town_hall", 1)
            entry.setdefault("cooldowns", {})
            entry.setdefault("boosts", {})
            entry.setdefault("achievements", [])
            entry.setdefault("stats", {})

            if gold is not None:
                entry["balance"] = max(0, int(gold))
                changes.append(f"Gold → **{entry['balance']:,}**")

            if clan_xp is not None:
                entry["clan_xp"] = max(0, int(clan_xp))
                changes.append(f"Clan XP → **{entry['clan_xp']:,}**")

            if gems is not None:
                entry["gems"] = max(0, int(gems))
                changes.append(f"Gems → **{entry['gems']:,}**")

            if medals is not None:
                entry["raid_medals"] = max(0, int(medals))
                changes.append(f"Raid Medals → **{entry['raid_medals']:,}**")

            if town_hall is not None:
                entry["town_hall"] = max(1, min(16, int(town_hall)))
                changes.append(f"Town Hall → **TH{entry['town_hall']}**")

            entry["name"] = name
            return stored

        await ctx.update_json_file(ctx.COINS_FILE, _update)

        if not changes:
            await interaction.response.send_message(
                "ℹ️ No values were changed. Add at least one field like `gold`, `clan_xp`, or `town_hall`.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            f"✅ Updated economy account for {member.mention}\n"
            + "\n".join(changes)
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