import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from discord import app_commands

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLASH_API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")

WAR_CHANNEL_ID = int(os.getenv("WAR_CHANNEL_ID"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))

LEADER_ROLE_ID = int(os.getenv("LEADER_ROLE_ID"))
CO_LEADER_ROLE_ID = int(os.getenv("CO_LEADER_ROLE_ID"))

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
LAST_DONATIONS_FILE = os.path.join(DATA_DIR, "last_donations.json")
WARNED_FILE = os.path.join(DATA_DIR, "warned_players.json")

headers = {
    "Authorization": f"Bearer {CLASH_API_KEY}",
    "Accept": "application/json"
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_saved_message(path):
    if os.path.exists(path):
        with open(path) as f:
            return int(f.read().strip())
    return None


def save_message(path, mid):
    with open(path, "w") as f:
        f.write(str(mid))


@tasks.loop(minutes=5)
async def update_loop():

    encoded_tag = CLAN_TAG.replace("#", "%23")

    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    try:
        war = requests.get(war_url, headers=headers).json()
        members = requests.get(members_url, headers=headers).json()["items"]
    except:
        print("API error")
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    state = war.get("state", "N/A")
    team_size = war.get("teamSize", 0)
    attacks_per_member = war.get("attacksPerMember", 2)

    end_time = war.get("endTime")

    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        time_remaining = str(end_dt - datetime.now(timezone.utc)).split(".")[0]
    else:
        time_remaining = "N/A"

    members_data = []
    total_attacks = 0

    warned_players = load_json(WARNED_FILE)
    new_warned = []

    for m in clan.get("members", []):

        attacks = m.get("attacks", [])

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        total_attacks += len(attacks)

        members_data.append({
            "name": m["name"],
            "attacks": len(attacks),
            "stars": stars,
            "destruction": destruction
        })

        if state == "inWar" and len(attacks) == 0:
            if m["name"] not in warned_players:
                new_warned.append(m["name"])
                warned_players[m["name"]] = True

    save_json(WARNED_FILE, warned_players)

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

    medals = ["🥇", "🥈", "🥉"]

    top = []
    tracker = []

    for i, m in enumerate(members_data):

        if i < 3 and m["stars"] > 0:
            top.append(f"{medals[i]} **{m['name']}**")

        warn = " ⚠️" if m["attacks"] == 0 else ""

        tracker.append(
            f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} • {m['stars']}⭐ • {m['destruction']}%{warn}"
        )

    embed = discord.Embed(
        title=f"⚔️ {clan.get('name')} vs {opponent.get('name','Opponent')}",
        description=(
            f"State: **{state}**\n"
            f"Team Size: **{team_size}v{team_size}**\n"
            f"Time Remaining: **{time_remaining}**\n\n"
            f"🔥 Attacks Used: **{total_attacks}/{team_size*attacks_per_member}**\n"
            f"⭐ Score: **{clan.get('stars',0)} — {opponent.get('stars',0)}**"
        ),
        color=0x2ECC71
    )

    embed.add_field(name="🥇 Top Performers", value="\n".join(top) if top else "No attacks yet", inline=False)
    embed.add_field(name="⚔️ Attack Tracker", value="\n\n".join(tracker), inline=False)

    channel = bot.get_channel(WAR_CHANNEL_ID)

    if channel:

        mid = get_saved_message(WAR_MESSAGE_FILE)

        try:

            if mid:

                msg = await channel.fetch_message(mid)
                await msg.edit(embed=embed)

            else:

                msg = await channel.send(embed=embed)
                save_message(WAR_MESSAGE_FILE, msg.id)

        except:

            msg = await channel.send(embed=embed)
            save_message(WAR_MESSAGE_FILE, msg.id)

    donations = {m["name"]: m["donations"] for m in members}

    last = load_json(LAST_DONATIONS_FILE)

    if donations != last:

        save_json(LAST_DONATIONS_FILE, donations)

        sorted_members = sorted(members, key=lambda x: x["donations"], reverse=True)

        leaderboard = []

        medals = ["🥇", "🥈", "🥉"]

        for i, m in enumerate(sorted_members[:10]):

            medal = medals[i] if i < 3 else "•"

            leaderboard.append(f"{medal} **{m['name']}** — {m['donations']}")

        embed = discord.Embed(
            title="🎁 Donation Leaderboard",
            description="\n".join(leaderboard),
            color=0xF1C40F
        )

        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)

        if channel:

            mid = get_saved_message(LEADERBOARD_MESSAGE_FILE)

            try:

                if mid:

                    msg = await channel.fetch_message(mid)
                    await msg.edit(embed=embed)

                else:

                    msg = await channel.send(embed=embed)
                    save_message(LEADERBOARD_MESSAGE_FILE, msg.id)

            except:

                msg = await channel.send(embed=embed)
                save_message(LEADERBOARD_MESSAGE_FILE, msg.id)


@tree.command(name="recruit", description="Generate recruitment embed")
async def recruit(interaction: discord.Interaction):

    roles = [role.id for role in interaction.user.roles]

    if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Join AM Allegiance",
        description="Relaxed war clan ⚔️",
        color=0xFFA500
    )

    embed.set_thumbnail(url="https://i.imgur.com/jXnZ622.png")
    embed.set_image(url="https://i.imgur.com/vNTiwib.png")

    await interaction.response.send_message(embed=embed)


@tree.command(name="clan", description="View clan info")
async def clan(interaction: discord.Interaction):

    encoded = CLAN_TAG.replace("#", "%23")

    url = f"https://api.clashofclans.com/v1/clans/{encoded}"

    clan = requests.get(url, headers=headers).json()

    embed = discord.Embed(
        title=f"{clan['name']} ({CLAN_TAG})",
        description=clan.get("description", ""),
        color=0xFFD700
    )

    embed.add_field(name="Members", value=f"{clan['members']}/50")
    embed.add_field(name="Trophies", value=clan["clanPoints"])
    embed.add_field(name="War Wins", value=clan["warWins"])

    embed.set_thumbnail(url=clan["badgeUrls"]["large"])

    await interaction.response.send_message(embed=embed)


@tree.command(name="stats", description="View player stats")
@app_commands.describe(player_tag="Player tag")
async def stats(interaction: discord.Interaction, player_tag: str):

    encoded = player_tag.replace("#", "%23")

    url = f"https://api.clashofclans.com/v1/players/{encoded}"

    player = requests.get(url, headers=headers).json()

    embed = discord.Embed(
        title=f"{player['name']} ({player_tag})",
        color=0x2ECC71
    )

    embed.add_field(name="Town Hall", value=player["townHallLevel"])
    embed.add_field(name="Trophies", value=player["trophies"])
    embed.add_field(name="War Stars", value=player["warStars"])
    embed.add_field(name="Donations", value=player["donations"])

    await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():

    print(f"Bot logged in as {bot.user}")

    await tree.sync()

    update_loop.start()


bot.run(DISCORD_TOKEN)