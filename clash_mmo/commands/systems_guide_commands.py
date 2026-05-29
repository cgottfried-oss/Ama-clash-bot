from __future__ import annotations

import discord
from discord import app_commands


TOPIC_CHOICES = [
    app_commands.Choice(name="Territories", value="territories"),
    app_commands.Choice(name="Clan War", value="clan_war"),
    app_commands.Choice(name="Cosmetics", value="cosmetics"),
    app_commands.Choice(name="Black Market", value="black_market"),
]


SYSTEM_GLOSSARY = {
    "territories": "Clan map-control regions that generate timed Gold income.",
    "clan war": "War/event performance system for attacks, MVP tracking, and rewards.",
    "cosmetics": "Identity/flex rewards such as banners, borders, titles, and effects. Some show small perks.",
    "black market": "Rotating rare-gear shop that acts as a Gold sink.",
    "gold sink": "A system that removes Gold from the economy to fight inflation.",
    "raidvillage": "NPC village attack loop for stars, Gold, XP, resources, ores, and chests.",
    "raiduser": "Player-vs-player loot attack command; replaces the old steal concept.",
    "bossattack": "Raid boss attack command for cooperative boss damage and rewards.",
    "mmo state": "The main persistent player data source: mmo_state.json.",
}

def register_systems_guide_commands(bot, ctx):
    @bot.tree.command(name="systemguide", description="Explain what major Clash MMO systems are for")
    @app_commands.describe(topic="System to explain")
    @app_commands.choices(topic=TOPIC_CHOICES)
    async def systemguide(interaction: discord.Interaction, topic: str = "territories"):
        topic = str(topic or "territories").strip().lower()
        embed = discord.Embed(title="Clash MMO System Guide", color=0x3498DB)

        if topic == "territories":
            embed.title = "🗺️ Territories"
            embed.description = (
                "Territories are the clan map-control loop. Claim regions, fight over regions, "
                "and collect periodic Gold income from owned regions."
            )
            embed.add_field(name="Commands", value="`/territorymap`, `/claimterritory`, `/attackterritory`, `/territoryincome`", inline=False)
            embed.add_field(name="Why it matters", value="Territories create clan-wide objectives and a shared Gold income loop outside normal farming.", inline=False)

        elif topic == "clan_war":
            embed.title = "⚔️ Clan War"
            embed.description = (
                "Clan War is the war-performance loop. It tracks war status, starts/ends war seasons, "
                "records war attacks, and feeds MVP/reward systems."
            )
            embed.add_field(name="Commands", value="`/warstatus`, `/startwar`, `/warattack`, `/endwar`", inline=False)
            embed.add_field(name="How it differs from territories", value="Clan War is match/event performance. Territories are persistent map ownership.", inline=False)

        elif topic == "cosmetics":
            embed.title = "🎨 Cosmetics"
            embed.description = (
                "Cosmetics are identity and flex rewards. They can be equipped to show titles, borders, "
                "banners, and effects. Some cosmetics now show small active perks."
            )
            embed.add_field(name="Commands", value="`/cosmetics`, `/equipcosmetic`, `/grantcosmetic`", inline=False)
            embed.add_field(name="Why it matters", value="Cosmetics give non-inflationary rewards that still feel meaningful without flooding the economy.", inline=False)

        elif topic == "black_market":
            embed.title = "🕶️ Black Market"
            embed.description = (
                "The Black Market is a rotating rare-gear shop and Gold sink. It gives players a way "
                "to spend Gold on targeted gear instead of only waiting for random drops."
            )
            embed.add_field(name="Commands", value="`/blackmarket`, `/blackmarketbuy`", inline=False)
            embed.add_field(name="Why it matters", value="It removes Gold from the economy while giving players exciting rare purchase options.", inline=False)

        else:
            embed.description = "Unknown topic."

        await interaction.response.send_message(embed=embed, ephemeral=True)


    @bot.tree.command(name="glossary", description="Look up Clash MMO terms and systems")
    @app_commands.describe(term="Term to look up")
    async def glossary(interaction: discord.Interaction, term: str = ""):
        query = str(term or "").strip().lower()

        if query:
            matches = [
                (name, definition)
                for name, definition in SYSTEM_GLOSSARY.items()
                if query in name.lower() or query in definition.lower()
            ]
        else:
            matches = list(SYSTEM_GLOSSARY.items())

        if not matches:
            await interaction.response.send_message(
                "No glossary entries matched that search.",
                ephemeral=True,
            )
            return

        lines = [
            f"**{name.title()}** — {definition}"
            for name, definition in matches[:12]
        ]

        embed = discord.Embed(
            title="📖 Clash MMO Glossary",
            description="\n".join(lines),
            color=0x5865F2,
        )
        embed.set_footer(text="Use /systemguide for longer system explanations.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
