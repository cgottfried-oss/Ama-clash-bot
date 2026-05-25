from __future__ import annotations

import random

import discord

from features.phase5.core.profiles import ensure_player_profile
from features.phase5.matchmaking import (
    format_league_profile,
    format_match_result,
    play_ranked_match,
)


PHASE5_PROFILE_FILE = "/app/data/phase5_profiles.json"



def register_economy_phase5_4_commands(bot, ctx):
    safe_load_json = ctx.safe_load_json
    update_json_file = ctx.update_json_file

    async def _profiles():
        data = await safe_load_json(PHASE5_PROFILE_FILE)

        if not isinstance(data, dict):
            data = {}

        data.setdefault("players", {})
        return data

    @bot.tree.command(name="league", description="View ranked league profile")
    async def league(interaction: discord.Interaction):
        data = await _profiles()

        player = ensure_player_profile(
            data,
            str(interaction.user.id),
            interaction.user.display_name,
        )

        embed = discord.Embed(
            title="🏆 Ranked League",
            description=format_league_profile(player),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="rankedbattle", description="Play a ranked PvP match")
    async def rankedbattle(interaction: discord.Interaction):
        data = await _profiles()

        players = data.setdefault("players", {})

        player = ensure_player_profile(
            data,
            str(interaction.user.id),
            interaction.user.display_name,
        )

        available = [
            profile
            for uid, profile in players.items()
            if uid != str(interaction.user.id)
        ]

        if not available:
            bot_profile = ensure_player_profile(
                data,
                "training_bot",
                "Training Bot",
            )

            available = [bot_profile]

        opponent = random.choice(available)

        result = play_ranked_match(player, opponent)

        def _update(container):
            container["players"] = data["players"]
            return container

        await update_json_file(PHASE5_PROFILE_FILE, _update)

        embed = discord.Embed(
            title="⚔️ Ranked Match",
            description=format_match_result(result),
            color=0xE74C3C,
        )

        embed.add_field(
            name="Opponent",
            value=opponent["identity"]["name"],
            inline=False,
        )

        await interaction.response.send_message(embed=embed)
