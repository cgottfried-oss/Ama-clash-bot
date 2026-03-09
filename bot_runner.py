import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import discord
from discord.ext import tasks
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

LEADER_ROLE_ID = int(os.getenv("LEADER_ROLE_ID"))       # Leader
CO_LEADER_ROLE_ID = int(os.getenv("CO_LEADER_ROLE_ID")) # Co-Leader

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

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
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

    # --------------------------
    # Build War Embed (ping individual users)
    # --------------------------
    members_data = []
    total_attacks = 0
    linked_players = load_linked_players()

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
    pings = []

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
    # Monthly Leaderboard
    # --------------------------
    month_key = datetime.now().strftime("%Y-%m")
    monthly = load_monthly()
    if month_key not in monthly:
        monthly[month_key] = {}
    for m in members:
        name = m["name"]
        donations = m["donations"]
        stars = monthly[month_key].get(name, {}).get("stars", 0)
        monthly[month_key][name] = {"donations": donations, "stars": stars}
    save_monthly(monthly)

    leaderboard = []
    for name, data in monthly[month_key].items():
        combined = data["donations"] + data["stars"]
        leaderboard.append({"name": name, "donations": data["donations"], "stars": data["stars"], "combined": combined})
    leaderboard.sort(key=lambda x: x["combined"], reverse=True)

    desc = ""
    for i, p in enumerate(leaderboard[:15], 1):
        desc += f"**{i}. {p['name']}**\n⭐ {p['stars']} | 🎁 {p['donations']} | 🔥 {p['combined']}\n\n"

    lb_embed = discord.Embed(title="🏆 AMA Monthly Gold Pass Leaderboard", description=desc, color=0xFFD700)
    lb_embed.set_footer(text=f"Month: {month_key}")

    lb_channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if lb_channel:
        mid = get_saved_message(LEADERBOARD_MESSAGE_FILE)
        try:
            if mid:
                msg = await lb_channel.fetch_message(mid)
                await msg.edit(embed=lb_embed)
            else:
                msg = await lb_channel.send(embed=lb_embed)
                save_message(LEADERBOARD_MESSAGE_FILE, msg.id)
        except:
            msg = await lb_channel.send(embed=lb_embed)
            save_message(LEADERBOARD_MESSAGE_FILE, msg.id)

# --------------------------
# /link Command
# --------------------------
@tree.command(name="link", description="Link your Discord account to your Clash tag")
@app_commands.describe(player_tag="Your in-game Clash tag")
async def link(interaction: discord.Interaction, player_tag: str):
    linked_players = load_linked_players()
    linked_players[player_tag] = interaction.user.id
    save_linked_players(linked_players)
    await interaction.response.send_message(f"✅ {interaction.user.mention} linked to {player_tag}", ephemeral=True)

# --------------------------
# /linked Command
# --------------------------
@tree.command(name="linked", description="See who is linked to which Clash accounts")
async def linked(interaction: discord.Interaction):
    linked_players = load_linked_players()
    if not linked_players:
        await interaction.response.send_message("No linked accounts yet.", ephemeral=True)
        return
    msg = "\n".join(f"<@{uid}> → {tag}" for tag, uid in linked_players.items())
    await interaction.response.send_message(msg, ephemeral=True)

# --------------------------
# /recruit Command (Leader/Co-Leader only, JSON template)
# --------------------------
@tree.command(name="recruit", description="Generate a recruitment embed message")
async def recruit(interaction: discord.Interaction):
    member_roles = [role.id for role in interaction.user.roles]
    if LEADER_ROLE_ID not in member_roles and CO_LEADER_ROLE_ID not in member_roles:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    embed_data = {
        "title": "Join AM Allegiance – Clash of Clans",
        "description": "⚔️ A relaxed farming clan with a competitive edge in wars and CWL! Whether you farm, donate, or attack, we have a place for you.",
        "color": 16753920,
        "fields": [
            {
                "name": "What We Offer",
                "value": "• Friendly, active community\n• War & CWL participation with automated attack reminders\n• Monthly leaderboards combining donations + war stars\n• Account linking with /link and /linked for personalized notifications"
            },
            {
                "name": "Clan Expectations",
                "value": "• Be respectful and stay active\n• Participate in war if opted in\n• Complete both attacks unless communicated otherwise\n• Link your Discord to your Clash account"
            },
            {
                "name": "How to Join",
                "value": "1️⃣ Check your TH level & war status in <#1477413528502665261>\n2️⃣ Link your Discord using `/link`\n3️⃣ Ping leadership for an invite"
            },
            {
                "name": "AMA Bot Highlights",
                "value": "• Live war tracking for each member\n• Personalized pings for members who haven’t attacked\n• Auto-updating monthly leaderboard\n• Persistent data storage for continuity"
            }
        ],
        "thumbnail": {"url": "https://i.imgur.com/yourClanLogo.png"},
        "image": {"url": "https://i.imgur.com/yourClanBanner.png"},
        "footer": {"text": "AM Allegiance • Clash of Clans"}
    }

    embed = discord.Embed(
        title=embed_data["title"],
        description=embed_data["description"],
        color=embed_data["color"]
    )

    for field in embed_data["fields"]:
        embed.add_field(name=field["name"], value=field["value"], inline=False)

    embed.set_thumbnail(url=embed_data["thumbnail"]["url"])
    embed.set_image(url=embed_data["image"]["url"])
    embed.set_footer(text=embed_data["footer"]["text"])

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