from __future__ import annotations

import discord


def build_changelog_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🔥 G.A.I.A – Recent Update Changelog",
        description="Latest stability, advisor, economy, rendering, and infrastructure updates.",
        color=0xFF7A1A,
    )
    sections = [
        ("🚀 Core System Improvements", "✅ Modular codebase structure\n✅ Removed duplicate helper logic\n✅ Centralized reward configuration\n✅ Improved data consistency across advisor, economy, and war tracking"),
        ("🧠 Advisor Engine Upgrades", "✅ Synced advisor categories with TH_CAPS\n✅ Improved scoring stability\n✅ Unified reward logic\n✅ Cleaner missing-data handling\n✅ Dynamic category grouping"),
        ("💰 Economy System Enhancements", "✅ Fixed deployment-blocking asyncio crash\n✅ Added automatic username tracking\n✅ Improved coin award data integrity\n✅ Fixed raw Discord IDs in leaderboards\n✅ Centralized war, clutch, advisor, and loot rewards"),
        ("🏆 Leaderboard Improvements", "✅ Better ID → display name resolution\n✅ Stronger fallback logic for uncached users\n✅ Prepared for HTML-rendered leaderboard cards"),
        ("🎨 HTML Rendering Expansion", "✅ Standardized Playwright render pipeline\n✅ Converted coin leaderboard, missing goals, and missing data to HTML cards\n✅ Added safe embed fallbacks\n✅ Unified style across war, donation, and advisor outputs"),
        ("⚙️ Infrastructure Improvements", "✅ Cleaner environment variable validation\n✅ Centralized async file locking\n✅ Reduced JSON corruption risk\n✅ Improved Coolify deployment reliability"),
        ("🧹 Bug Fixes", "🛠 Fixed broken multiline string crash\n🛠 Fixed economy initialization crash\n🛠 Fixed duplicate logic inconsistencies\n🛠 Fixed leaderboard name desync\n🛠 Fixed advisor reward mismatch edge cases"),
        ("🧩 New Internal Systems", "🧱 storage.py — centralized file I/O\n🔗 linked_accounts.py — consistent account linking\n🎁 reward_config.py — single source of truth for rewards"),
    ]
    for name, value in sections:
        embed.add_field(name=name, value=value, inline=False)
    embed.add_field(
        name="🧠 What This Means",
        value="G.A.I.A is now more stable, easier to maintain, more consistent across features, visually unified, and ready for future expansion.",
        inline=False,
    )
    embed.set_footer(text="G.A.I.A System Update • Clean Build")
    return embed


def register_changelog(bot, ctx):
    @bot.tree.command(name="changelog", description="View latest G.A.I.A updates")
    async def changelog(interaction: discord.Interaction):
        await interaction.response.send_message(embed=build_changelog_embed())
