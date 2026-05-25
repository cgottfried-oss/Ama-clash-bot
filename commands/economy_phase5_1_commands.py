from __future__ import annotations

import random

import discord
from discord import app_commands

from features.phase5.seasonal_system import (
    BATTLE_PASS_REWARDS,
    add_season_xp,
    current_season_key,
    ensure_player,
    get_leaderboard,
    get_league_name,
    load_state,
    update_rating,
)


def register_economy_phase5_1_commands(bot, ctx):
    update_json_file = ctx.update_json_file
    COINS_FILE = ctx.COINS_FILE

    async def _grant_rewards(user_id: str, reward: dict, name: str):
        def _update(stored):
            if not isinstance(stored, dict):
                stored = {}

            users = stored.setdefault("users", {})
            entry = users.setdefault(user_id, {
                "balance": 0,
                "gems": 0,
                "raid_medals": 0,
                "name": name,
            })

            entry["balance"] = int(entry.get("balance", 0) or 0) + int(reward.get("gold", 0) or 0)
            entry["gems"] = int(entry.get("gems", 0) or 0) + int(reward.get("gems", 0) or 0)
            entry["raid_medals"] = int(entry.get("raid_medals", 0) or 0) + int(reward.get("medals", 0) or 0)

            cosmetics = entry.setdefault("cosmetics", {})

            if reward.get("title"):
                cosmetics.setdefault("titles", []).append(reward["title"])

            if reward.get("border"):
                cosmetics.setdefault("borders", []).append(reward["border"])

            return stored

        await update_json_file(COINS_FILE, _update)

    @bot.tree.command(name="season", description="View your Phase 5 seasonal ladder stats")
    async def p5season(interaction: discord.Interaction):
        await ensure_player(ctx, str(interaction.user.id), interaction.user.display_name)

        data = await load_state(ctx)
        season_key = current_season_key()

        user = (
            data.get("seasons", {})
            .get(season_key, {})
            .get("users", {})
            .get(str(interaction.user.id), {})
        )

        rating = int(user.get("rating", 1000) or 1000)
        league = get_league_name(rating)

        embed = discord.Embed(
            title=f"🏆 Phase 5 Season {season_key}",
            color=0xF1C40F,
        )

        embed.add_field(name="League", value=f"**{league}**", inline=True)
        embed.add_field(name="Rating", value=f"**{rating:,}**", inline=True)
        embed.add_field(name="Battle Pass Tier", value=f"**{user.get('battle_pass_tier', 1)}**", inline=True)
        embed.add_field(name="Wins", value=str(user.get("wins", 0)), inline=True)
        embed.add_field(name="Losses", value=str(user.get("losses", 0)), inline=True)
        embed.add_field(name="Season XP", value=str(user.get("season_xp", 0)), inline=True)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="battlepass", description="View Phase 5 battle pass rewards")
    async def p5battlepass(interaction: discord.Interaction):
        lines = []

        for tier, reward in BATTLE_PASS_REWARDS.items():
            reward_text = ", ".join([f"{k}: {v}" for k, v in reward.items()])
            lines.append(f"Tier **{tier}** — {reward_text}")

        embed = discord.Embed(
            title="🎟️ Phase 5 Battle Pass",
            description="\n".join(lines),
            color=0x2ECC71,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="claimpass", description="Claim your Phase 5 battle pass rewards")
    async def p5claimpass(interaction: discord.Interaction):
        await ensure_player(ctx, str(interaction.user.id), interaction.user.display_name)

        data = await load_state(ctx)
        season_key = current_season_key()

        user = (
            data.get("seasons", {})
            .get(season_key, {})
            .get("users", {})
            .get(str(interaction.user.id), {})
        )

        tier = int(user.get("battle_pass_tier", 1) or 1)
        claimed = set(user.get("claimed_tiers", []))

        available = [t for t in BATTLE_PASS_REWARDS if t <= tier and t not in claimed]

        if not available:
            await interaction.response.send_message("No Phase 5 battle pass rewards ready to claim.", ephemeral=True)
            return

        for unlocked in available:
            await _grant_rewards(
                str(interaction.user.id),
                BATTLE_PASS_REWARDS[unlocked],
                interaction.user.display_name,
            )

        def _update(data_state):
            season = data_state.setdefault("seasons", {}).setdefault(season_key, {})
            users = season.setdefault("users", {})
            entry = users.setdefault(str(interaction.user.id), {})
            existing = set(entry.get("claimed_tiers", []))
            existing.update(available)
            entry["claimed_tiers"] = sorted(existing)
            return data_state

        await update_json_file(f"{ctx.DATA_DIR}/phase5_seasons.json", _update)

        await interaction.response.send_message(
            f"🎁 Claimed Phase 5 battle pass rewards for tiers: **{', '.join(map(str, available))}**"
        )

    @bot.tree.command(name="leaderboard", description="View the Phase 5 seasonal leaderboard")
    async def p5leaderboard(interaction: discord.Interaction):
        leaders = await get_leaderboard(ctx)

        if not leaders:
            await interaction.response.send_message("No Phase 5 ranked players yet.", ephemeral=True)
            return

        lines = []

        for idx, (_, data) in enumerate(leaders, start=1):
            rating = int(data.get("rating", 0) or 0)
            league = get_league_name(rating)
            lines.append(
                f"#{idx} **{data.get('name', 'Unknown')}** — {rating:,} MMR ({league})"
            )

        embed = discord.Embed(
            title="🌍 Phase 5 Seasonal Leaderboard",
            description="\n".join(lines),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)
