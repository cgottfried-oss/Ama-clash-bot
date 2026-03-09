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

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
MONTHLY_FILE = os.path.join(DATA_DIR, "monthly_data.json")
LINKED_FILE = os.path.join(DATA_DIR, "linked_players.json")

# --------------------------
# Discord Client
# --------------------------
intents = discord.Intents.default()
intents.members = True  # Required for fetching members
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

headers = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}

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

def load_linked():
    if os.path.exists(LINKED_FILE):
        with open(LINKED_FILE) as f:
            return json.load(f)
    return {}

def save_linked(data):
    with open(LINKED_FILE, "w") as f:
        json.dump(data, f, indent=2)

# --------------------------
# /link command
# --------------------------
@tree.command(name="link", description="Link your Discord account to your Clash player tag")
@app_commands.describe(tag="Your Clash player tag, e.g., #L0PY0YGL")
async def link(interaction: discord.Interaction, tag: str):
    linked = load_linked()
    linked[tag] = str(interaction.user.id)
    save_linked(linked)
    await interaction.response.send_message(f"{interaction.user.mention} linked to {tag}", ephemeral=True)

# --------------------------
# /linked command
# --------------------------
@tree.command(name="linked", description="See all Discord users linked to Clash player tags")
async def linked(interaction: discord.Interaction):
    linked_data = load_linked()
    if not linked_data:
        await interaction.response.send_message("No players have linked yet.", ephemeral=True)
        return

    lines = []
    for tag, discord_id in linked_data.items():
        user = interaction.guild.get_member(int(discord_id))
        username = user.mention if user else f"<@{discord_id}>"
        lines.append(f"{username} → {tag}")

    message = "\n".join(lines)
    if len(message) > 1900:
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            await interaction.response.send_message(chunk, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

# --------------------------
# Main Loop
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
    # Build War Embed
    # --------------------------
    members_data = []
    total_attacks = 0

    linked_players = load_linked()

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
    top, tracker = [], []

    for i, m in enumerate(members_data):
        if i < 3 and m["stars"] > 0:
            top.append(f"{medals[i]} **{m['name']}**")
        # Ping linked user if they haven't attacked
        warn = ""
        for tag, discord_id in linked_players.items():
            if m["name"] == tag and m["attacks"] == 0 and state == "inWar":
                warn = f" ⚠️ <@{discord_id}>"
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
# Bot Ready
# --------------------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await tree.sync()
    update_loop.start()

bot.run(DISCORD_TOKEN)