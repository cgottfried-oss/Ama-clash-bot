from __future__ import annotations

import random

import discord
from discord import app_commands

from clash_mmo.game.seasonal_system import (
    BATTLE_PASS_REWARDS,
    add_season_xp,
    current_season_key,
    ensure_player,
    get_leaderboard,
    get_league_name,
    load_state,
    update_rating,
)
from clash_mmo.game.state import update_mmo_state
from clash_mmo.game.core.profiles import ensure_player_profile


def register_season_commands(bot, ctx):

    async def _grant_rewards(user_id: str, reward: dict, name: str):
        def _update(state):
            if not isinstance(state, dict):
                state = {}
    
            profile = ensure_player_profile(state, str(user_id), name)
    
            gold = int(reward.get("gold", 0) or 0)
            gems = int(reward.get("gems", 0) or 0)
            medals = int(reward.get("medals", 0) or 0)
    
            profile["gold"] = max(0, int(profile.get("gold", 0) or 0) + gold)
            profile["gems"] = max(0, int(profile.get("gems", 0) or 0) + gems)
            profile["raid_medals"] = max(0, int(profile.get("raid_medals", 0) or 0) + medals)
    
            stats = profile.setdefault("stats", {})
            if gold > 0:
                stats["lifetime_gold"] = int(stats.get("lifetime_gold", 0) or 0) + gold
    
            cosmetics = profile.setdefault("cosmetics", {})
    
            if reward.get("title"):
                titles = cosmetics.setdefault("titles", [])
                if reward["title"] not in titles:
                    titles.append(reward["title"])
    
            if reward.get("border"):
                borders = cosmetics.setdefault("borders", [])
                if reward["border"] not in borders:
                    borders.append(reward["border"])
    
            identity = profile.setdefault("identity", {})
            identity["display_name"] = name
            profile["name"] = name
    
            return state
    
        await update_mmo_state(ctx, _update)

    @bot.tree.command(name="seasonstats", description="View your seasonal ladder stats")
    async def seasonstats(interaction: discord.Interaction):
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
            title=f"🏆 Season {season_key}",
            color=0xF1C40F,
        )

        embed.add_field(name="League", value=f"**{league}**", inline=True)
        embed.add_field(name="Rating", value=f"**{rating:,}**", inline=True)
        embed.add_field(name="Battle Pass Tier", value=f"**{user.get('battle_pass_tier', 1)}**", inline=True)
        embed.add_field(name="Wins", value=str(user.get("wins", 0)), inline=True)
        embed.add_field(name="Losses", value=str(user.get("losses", 0)), inline=True)
        embed.add_field(name="Season XP", value=str(user.get("season_xp", 0)), inline=True)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="battlepass", description="View battle pass rewards")
    async def battlepass(interaction: discord.Interaction):
        lines = []

        for tier, reward in BATTLE_PASS_REWARDS.items():
            reward_text = ", ".join([f"{k}: {v}" for k, v in reward.items()])
            lines.append(f"Tier **{tier}** — {reward_text}")

        embed = discord.Embed(
            title="🎟️ Battle Pass",
            description="\n".join(lines),
            color=0x2ECC71,
        )

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="claimpass", description="Claim your battle pass rewards")
    async def claimpass(interaction: discord.Interaction):
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
            await interaction.response.send_message("No battle pass rewards ready to claim.", ephemeral=True)
            return

        for unlocked in available:
            await _grant_rewards(
                str(interaction.user.id),
                BATTLE_PASS_REWARDS[unlocked],
                interaction.user.display_name,
            )

        def _update(data_state):
            seasons_container = data_state.setdefault("seasons", {})
            season = seasons_container.setdefault("seasons", {}).setdefault(season_key, {})
            users = season.setdefault("users", {})
            entry = users.setdefault(str(interaction.user.id), {})
            existing = set(entry.get("claimed_tiers", []))
            existing.update(available)
            entry["claimed_tiers"] = sorted(existing)
            return data_state

        await update_mmo_state(ctx, _update)

        await interaction.response.send_message(
            f"🎁 Claimed battle pass rewards for tiers: **{', '.join(map(str, available))}**"
        )

    @bot.tree.command(name="seasonleaderboard", description="View the seasonal leaderboard")
    async def seasonleaderboard(interaction: discord.Interaction):
        leaders = await get_leaderboard(ctx)

        if not leaders:
            await interaction.response.send_message("No ranked players yet.", ephemeral=True)
            return

        lines = []

        for idx, (_, data) in enumerate(leaders, start=1):
            rating = int(data.get("rating", 0) or 0)
            league = get_league_name(rating)
            lines.append(
                f"#{idx} **{data.get('name', 'Unknown')}** — {rating:,} MMR ({league})"
            )

        embed = discord.Embed(
            title="🌍 Seasonal Leaderboard",
            description="\n".join(lines),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)
