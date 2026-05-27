from __future__ import annotations

import discord
from discord import app_commands

from clash_mmo.game.state import update_mmo_state


def register_admin_commands(bot, ctx):
    def _is_owner(interaction: discord.Interaction) -> bool:
        return int(interaction.user.id) == int(getattr(ctx, "MMO_OWNER_ID", 0) or 0)

    @bot.tree.command(name="mmoadminreset", description="Owner: wipe a player's Clash MMO data")
    @app_commands.describe(
        user="Discord user whose MMO data should be wiped",
        wipe_economy="Also wipe coins, gems, medals, chests, shop inventory, cooldowns, and TH progress",
        wipe_mmo="Wipe MMO profile, heroes, gear, PvP, raids participation, and MMO state profile",
    )
    async def mmoadminreset(
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
            wiped.append("economy")

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