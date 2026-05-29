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
    get_battle_pass_progress,
    format_battle_pass_reward,
    roll_battle_pass_reward,
    load_state,
    update_rating,
)
from clash_mmo.game.state import update_mmo_state
from clash_mmo.game.core.profiles import ensure_player_profile


def register_season_commands(bot, ctx):

    async def _grant_rewards(user_id: str, reward: dict, name: str):
        rolled = roll_battle_pass_reward(reward)
        resolved = rolled["resolved"]

        def _update(state):
            if not isinstance(state, dict):
                state = {}

            profile = ensure_player_profile(state, str(user_id), name)

            resource_map = {
                "gold": "gold",
                "elixir": "elixir",
                "dark_elixir": "dark_elixir",
                "gems": "gems",
                "medals": "raid_medals",
                "raid_medals": "raid_medals",
                "shiny_ore": "shiny_ore",
                "glowy_ore": "glowy_ore",
                "starry_ore": "starry_ore",
            }

            for reward_key, profile_key in resource_map.items():
                amount = int(resolved.get(reward_key, 0) or 0)
                if amount <= 0:
                    continue
                profile[profile_key] = max(0, int(profile.get(profile_key, 0) or 0) + amount)

            stats = profile.setdefault("stats", {})
            if int(resolved.get("gold", 0) or 0) > 0:
                stats["lifetime_gold"] = int(stats.get("lifetime_gold", 0) or 0) + int(resolved.get("gold", 0) or 0)

            cosmetics = profile.setdefault("cosmetics", {})

            if resolved.get("title"):
                owned = cosmetics.setdefault("owned", {})
                titles = owned.setdefault("titles", [])
                if resolved["title"] not in titles:
                    titles.append(resolved["title"])

            if resolved.get("border"):
                owned = cosmetics.setdefault("owned", {})
                borders = owned.setdefault("borders", [])
                if resolved["border"] not in borders:
                    borders.append(resolved["border"])

            identity = profile.setdefault("identity", {})
            identity["display_name"] = name
            profile["name"] = name

            return state

        await update_mmo_state(ctx, _update)
        return rolled

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
        pass_progress = get_battle_pass_progress(user)
        embed.add_field(
            name="Battle Pass",
            value=(
                f"Tier **{pass_progress['tier']}**\n"
                f"XP: **{pass_progress['season_xp']:,}/{pass_progress['xp_needed']:,}**\n"
                f"Claimable: **{len(pass_progress['claimable_tiers'])}**"
            ),
            inline=True,
        )
        embed.add_field(name="Wins", value=str(user.get("wins", 0)), inline=True)
        embed.add_field(name="Losses", value=str(user.get("losses", 0)), inline=True)
        embed.add_field(name="Season XP", value=str(user.get("season_xp", 0)), inline=True)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="battlepass", description="View battle pass rewards")
    async def battlepass(interaction: discord.Interaction):
        await ensure_player(ctx, str(interaction.user.id), interaction.user.display_name)

        data = await load_state(ctx)
        season_key = current_season_key()
        user = (
            data.get("seasons", {})
            .get("seasons", {})
            .get(season_key, {})
            .get("users", {})
            .get(str(interaction.user.id), {})
        )
        progress = get_battle_pass_progress(user)

        lines = []
        for tier, reward in BATTLE_PASS_REWARDS.items():
            marker = "✅" if tier in progress["claimed_tiers"] else ("🎁" if tier in progress["claimable_tiers"] else "🔒")
            reward_text = format_battle_pass_reward(reward)
            lines.append(f"{marker} Tier **{tier}** — {reward_text}")

        embed = discord.Embed(
            title=f"🎟️ Battle Pass — Season {season_key}",
            description="\n".join(lines),
            color=0x2ECC71,
        )
        embed.add_field(
            name="Your Progress",
            value=(
                f"Tier **{progress['tier']}**\n"
                f"XP: **{progress['season_xp']:,}/{progress['xp_needed']:,}**\n"
                f"Rewards ready: **{len(progress['claimable_tiers'])}**"
            ),
            inline=False,
        )
        embed.set_footer(text="Earn Season XP from ranked/season systems, then use /claimpass to collect unlocked rewards.")

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

        rolled_rewards = []
        for unlocked in available:
            rolled = await _grant_rewards(
                str(interaction.user.id),
                BATTLE_PASS_REWARDS[unlocked],
                interaction.user.display_name,
            )
            rolled_rewards.append((unlocked, rolled))

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

        bonus_lines = []
        for tier_id, rolled in rolled_rewards:
            chance_awards = [
                f"{key.replace('_', ' ').title()} +{details.get('awarded')}"
                for key, details in rolled.get("chance_details", {}).items()
                if int(details.get("awarded", 0) or 0) > 0
            ]
            if chance_awards:
                bonus_lines.append(f"Tier {tier_id}: " + ", ".join(chance_awards))

        message = f"🎁 Claimed battle pass rewards for tiers: **{', '.join(map(str, available))}**"
        if bonus_lines:
            message += "\n✨ Bonus rolls hit:\n" + "\n".join(bonus_lines)

        await interaction.response.send_message(message)



    @bot.tree.command(name="battlepassinfo", description="Explain how the battle pass works")
    async def battlepassinfo(interaction: discord.Interaction):
        embed = discord.Embed(title="🎟️ How Battle Pass Works", color=0x2ECC71)
        embed.description = (
            "The battle pass is the seasonal reward track. You earn **Season XP**, unlock tiers, "
            "then claim all unlocked tier rewards with `/claimpass`."
        )
        embed.add_field(name="Check progress", value="Use `/seasonstats` or `/battlepass`.", inline=False)
        embed.add_field(name="Claim rewards", value="Use `/claimpass` when tiers are unlocked.", inline=False)
        embed.add_field(name="Tier cost", value="Each tier costs more Season XP than the last.", inline=False)
        embed.add_field(
            name="Reward types",
            value="Gold, Gems, Raid Medals, Titles, Borders, and future seasonal rewards.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
