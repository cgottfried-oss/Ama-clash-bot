from __future__ import annotations

import discord


def register_rpg_guide_commands(bot, ctx):
    LEADER_ROLE_ID = getattr(ctx, "LEADER_ROLE_ID", 0)
    CO_LEADER_ROLE_ID = getattr(ctx, "CO_LEADER_ROLE_ID", 0)

    def _is_admin(member) -> bool:
        if not isinstance(member, discord.Member):
            return False
        return any(role.id in {LEADER_ROLE_ID, CO_LEADER_ROLE_ID} for role in member.roles)

    def _guide_embeds():
        intro = discord.Embed(
            title="📘 AM Allegiance Clash RPG/MMO Guide",
            description=(
                "Welcome to our custom Clash-inspired Discord RPG/MMO.\n\n"
                "Build your village, collect loot, upgrade your Town Hall, level heroes, raid other members, "
                "fight clan bosses, compete in seasons, and help the clan grow."
            ),
            color=0x3498DB,
        )
        intro.add_field(
            name="Quick Start",
            value=(
                "1. `/daily` — collect daily loot\n"
                "2. `/farm` — grind Gold, Gems, and Clan XP\n"
                "3. `/train` — gain extra Clan XP\n"
                "4. `/upgradehall` — level your Town Hall\n"
                "5. `/village` — check your profile\n"
                "6. `/economyhelp` — view basic commands"
            ),
            inline=False,
        )
        intro.add_field(
            name="Main Resources",
            value="Gold • Gems • Raid Medals • Clan XP • Dark Elixir",
            inline=False,
        )

        progression = discord.Embed(title="🏰 Progression & Economy", color=0xF1C40F)
        progression.add_field(
            name="Town Hall Unlocks",
            value=(
                "**TH1** — `/daily`, `/farm`, `/train`\n"
                "**TH3** — `/raid`\n"
                "**TH4** — `/raiduser`\n"
                "**TH5** — `/openchest`\n"
                "**TH7** — better chest odds + Legend Chest\n"
                "**TH9** — Dark Elixir\n"
                "**TH10+** — stronger late-game hero progression"
            ),
            inline=False,
        )
        progression.add_field(
            name="Shop & Items",
            value=(
                "Use `/shop`, `/buy`, `/inventory`, `/useitem`, and `/useeconomyitem`.\n\n"
                "Useful items include Training Potion, Resource Potion, Builder Potion, Book of Heroes, Rune of Gold, Legend Chest, Loot Shield, and War Banner."
            ),
            inline=False,
        )
        progression.add_field(
            name="Achievements",
            value="Use `/achievements` to view goals and earn bonus Gold.",
            inline=False,
        )

        clan = discord.Embed(title="🏦 Clan Systems", color=0x2ECC71)
        clan.add_field(
            name="Clan Bank",
            value=(
                "`/clanbank` — view treasury and upgrades\n"
                "`/clandonate amount` — donate Gold to the clan\n"
                "`/clanupgrade` — leader/co-leader upgrade tool"
            ),
            inline=False,
        )
        clan.add_field(
            name="Clan Boss Raids",
            value=(
                "`/boss` — view current boss\n"
                "`/bossattack` — attack once per cooldown\n"
                "`/claimbossrewards` — claim after victory\n"
                "Leaders can start bosses with `/startboss`."
            ),
            inline=False,
        )
        clan.add_field(
            name="Seasons",
            value="Use `/season`, `/claimseason`, and `/seasonleaderboard` to track monthly progress.",
            inline=False,
        )

        combat = discord.Embed(title="⚔️ PvP, Heroes & War", color=0xE74C3C)
        combat.add_field(
            name="User Raiding",
            value=(
                "`/raiduser @member` — raid another village\n"
                "`/revenge` — strike back after being raided\n"
                "`/bounty @member amount` — place a bounty"
            ),
            inline=False,
        )
        combat.add_field(
            name="Heroes",
            value=(
                "`/heroes` — view your roster\n"
                "`/upgradehero king`\n"
                "`/upgradehero queen`\n"
                "`/upgradehero warden`\n"
                "`/upgradehero champion`"
            ),
            inline=False,
        )
        combat.add_field(
            name="Clan Wars 2.0",
            value=(
                "`/war2attack` — use a War 2.0 attack\n"
                "`/war2status` — view score\n"
                "Leaders can use `/startwar2` and `/endwar2`."
            ),
            inline=False,
        )
        combat.add_field(
            name="Procedural Events",
            value="Use `/eventstatus` to see active events. Leaders can start events with `/startevent`.",
            inline=False,
        )

        routine = discord.Embed(title="✅ Recommended Daily Routine", color=0x9B59B6)
        routine.description = (
            "1. `/daily`\n"
            "2. `/farm`\n"
            "3. `/train`\n"
            "4. `/raid` once unlocked\n"
            "5. `/openchest` once unlocked\n"
            "6. `/bossattack` if a boss is active\n"
            "7. `/war2attack` if War 2.0 is active\n"
            "8. `/claimseason` when rewards are available\n"
            "9. `/village` to check progress"
        )

        roadmap = discord.Embed(title="🔮 Future Phase 5 Roadmap", color=0x5865F2)
        roadmap.add_field(
            name="Equipment & Rarity",
            value="Common, rare, epic, and legendary gear with stat modifiers and hero builds.",
            inline=False,
        )
        roadmap.add_field(
            name="Matchmaking",
            value="MMR, leagues, and Elo ladder for fair competitive progression.",
            inline=False,
        )
        roadmap.add_field(
            name="Clan Territory Map",
            value="Region ownership, seasonal conquest, and passive resource generation.",
            inline=False,
        )
        roadmap.add_field(
            name="Real-Time PvE",
            value="Cooperative raid bosses with timed damage windows, abilities, and phases.",
            inline=False,
        )
        roadmap.add_field(
            name="Marketplace",
            value="Player trading, auction house, and black market trader.",
            inline=False,
        )
        roadmap.add_field(
            name="AI-Generated Events",
            value="Random invasions, seasonal story arcs, and dynamic economy fluctuations.",
            inline=False,
        )

        return [intro, progression, clan, combat, routine, roadmap]

    @bot.tree.command(name="rpgguide", description="Post the Clash RPG/MMO player guide")
    async def rpgguide(interaction: discord.Interaction):
        embeds = _guide_embeds()
        await interaction.response.send_message(embeds=embeds[:3])
        await interaction.followup.send(embeds=embeds[3:])

    @bot.tree.command(name="postrpgguide", description="Leader tool: post the RPG guide publicly in this channel")
    async def postrpgguide(interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("❌ Leaders and co-leaders only.", ephemeral=True)
            return
        embeds = _guide_embeds()
        await interaction.response.send_message("📘 Posting the RPG/MMO guide in this channel...", ephemeral=True)
        await interaction.channel.send(embeds=embeds[:3])
        await interaction.channel.send(embeds=embeds[3:])
