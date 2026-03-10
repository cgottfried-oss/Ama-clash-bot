import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from discord import app_commands

load_dotenv()

# --------------------------
# Environment Variables
# --------------------------
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
MONTHLY_FILE = os.path.join(DATA_DIR, "monthly_data.json")
LINKED_PLAYERS_FILE = os.path.join(DATA_DIR, "linked_players.json")

headers = {
    "Authorization": f"Bearer {CLASH_API_KEY}",
    "Accept": "application/json"
}

# --------------------------
# Intents & Bot
# --------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# --------------------------
# Helper Functions
# --------------------------
def get_saved_message(path):
    if os.path.exists(path):
        with open(path) as f:
            return int(f.read().strip())
    return None

def save_message(path, mid):
    with open(path, "w") as f:
        f.write(str(mid))

def load_monthly():
    if os.path.exists(MONTHLY_FILE):
        with open(MONTHLY_FILE) as f:
            return json.load(f)
    return {}

def save_monthly(data):
    with open(MONTHLY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_linked_players():
    if os.path.exists(LINKED_PLAYERS_FILE):
        with open(LINKED_PLAYERS_FILE) as f:
            return json.load(f)
    return {}

def save_linked_players(data):
    with open(LINKED_PLAYERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------------------------
# War & Leaderboard Loop
# --------------------------
@tasks.loop(minutes=10)
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
    linked_players = load_linked_players()
    pings = []

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

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)
    medals = ["🥇", "🥈", "🥉"]

    top = []
    tracker = []

    for i, m in enumerate(members_data):
        if i < 3 and m["stars"] > 0:
            top.append(f"{medals[i]} **{m['name']}**")
        warn = ""
        if m["attacks"] == 0 and state == "inWar":
            warn = " ⚠️"
            discord_id = linked_players.get(m["name"])
            if discord_id:
                pings.append(f"<@{discord_id}>")
        tracker.append(f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} • {m['stars']}⭐ • {m['destruction']}%{warn}")

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
    embed.set_footer(text="AMA Bot • Auto Updates")

    channel = bot.get_channel(WAR_CHANNEL_ID)
    alert_text = " ".join(pings) if pings else None

    if channel:
        mid = get_saved_message(WAR_MESSAGE_FILE)
        try:
            if mid:
                msg = await channel.fetch_message(mid)
                await msg.edit(content=alert_text, embed=embed)
            else:
                msg = await channel.send(content=alert_text, embed=embed)
                save_message(WAR_MESSAGE_FILE, msg.id)
        except:
            msg = await channel.send(content=alert_text, embed=embed)
            save_message(WAR_MESSAGE_FILE, msg.id)

# --------------------------
# /stats Command
# --------------------------
@tree.command(name="stats", description="View a player's Clash of Clans stats")
@app_commands.describe(player_tag="Player tag (leave empty if linked)")
async def stats(interaction: discord.Interaction, player_tag: str = None):

    linked_players = load_linked_players()

    if not player_tag:
        for tag, uid in linked_players.items():
            if uid == interaction.user.id:
                player_tag = tag
                break

    if not player_tag:
        await interaction.response.send_message(
            "No tag provided and no linked account found. Use `/link` first.",
            ephemeral=True
        )
        return

    encoded_tag = player_tag.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"

    player = requests.get(url, headers=headers).json()

    embed = discord.Embed(
        title=f"{player['name']} ({player_tag})",
        color=0x2ECC71
    )

    embed.add_field(name="🏰 Town Hall", value=player.get("townHallLevel", "N/A"))
    embed.add_field(name="🏆 Trophies", value=player.get("trophies", "N/A"))
    embed.add_field(name="⭐ War Stars", value=player.get("warStars", "N/A"))
    embed.add_field(name="🎁 Donations", value=player.get("donations", "N/A"))
    embed.add_field(name="📥 Donations Received", value=player.get("donationsReceived", "N/A"))

    await interaction.response.send_message(embed=embed)

# --------------------------
# /clan Command
# --------------------------
@tree.command(name="clan", description="View clan information")
async def clan(interaction: discord.Interaction):

    encoded_tag = CLAN_TAG.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}"

    clan = requests.get(url, headers=headers).json()

    embed = discord.Embed(
        title=f"{clan['name']} ({CLAN_TAG})",
        description=clan.get("description", ""),
        color=0xFFD700
    )

    embed.add_field(name="👥 Members", value=f"{clan['members']}/50")
    embed.add_field(name="🏆 Clan Trophies", value=clan.get("clanPoints", "N/A"))
    embed.add_field(name="⚔️ War Wins", value=clan.get("warWins", "N/A"))
    embed.add_field(name="🔥 Win Streak", value=clan.get("warWinStreak", "N/A"))

    embed.set_thumbnail(url=clan.get("badgeUrls", {}).get("large"))

    await interaction.response.send_message(embed=embed)

# --------------------------
# /recruit Command
# --------------------------
@tree.command(name="recruit", description="Generate a recruitment embed message")
async def recruit(interaction: discord.Interaction):

    member_roles = [role.id for role in interaction.user.roles]
    if LEADER_ROLE_ID not in member_roles and CO_LEADER_ROLE_ID not in member_roles:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Join AM Allegiance – Clash of Clans",
        description="⚔️ A relaxed farming clan with a competitive edge in wars and CWL!",
        color=0xFFA500
    )

    embed.set_thumbnail(url="https://i.imgur.com/jXnZ622.png")
    embed.set_image(url="https://i.imgur.com/vNTiwib.png")
    embed.set_footer(text="AM Allegiance • Clash of Clans")

    await interaction.response.send_message(embed=embed)

# --------------------------
# Bot Ready
# --------------------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await tree.sync()
    update_loop.start()

bot.run(DISCORD_TOKEN)
