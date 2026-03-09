import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import discord
from discord.ext import tasks

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLASH_API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")

WAR_CHANNEL_ID = int(os.getenv("WAR_CHANNEL_ID"))
WAR_ROLE_ID = int(os.getenv("WAR_ROLE_ID"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

WAR_ALERT_FILE = os.path.join(DATA_DIR, "war_alerts.txt")
WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
MONTHLY_FILE = os.path.join(DATA_DIR, "monthly_data.json")
LINKED_PLAYERS_FILE = os.path.join(DATA_DIR, "linked_players.json")

# --------------------------
# Load / Save Helpers
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

def load_links():
    if os.path.exists(LINKED_PLAYERS_FILE):
        with open(LINKED_PLAYERS_FILE) as f:
            return json.load(f)
    return {}

def save_links(data):
    with open(LINKED_PLAYERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

linked_players = load_links()

# --------------------------
# War Alert Helpers
# --------------------------

def has_alert(alert):
    if not os.path.exists(WAR_ALERT_FILE):
        return False
    with open(WAR_ALERT_FILE) as f:
        return alert in f.read().splitlines()

def log_alert(alert):
    with open(WAR_ALERT_FILE, "a") as f:
        f.write(alert + "\n")

def reset_alerts():
    if os.path.exists(WAR_ALERT_FILE):
        os.remove(WAR_ALERT_FILE)

def get_missing_attack_pings(clan_members, attacks_per_member):
    pings = []
    for m in clan_members:
        tag = m.get("tag")
        attacks = len(m.get("attacks", []))
        if attacks < attacks_per_member:
            if tag in linked_players:
                pings.append(f"<@{linked_players[tag]}>")
    return " ".join(pings)

# --------------------------
# Discord Bot Setup
# --------------------------

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

headers = {
    "Authorization": f"Bearer {CLASH_API_KEY}",
    "Accept": "application/json"
}

# --------------------------
# /link Command
# --------------------------

@tree.command(name="link", description="Link your Clash player tag to your Discord account")
async def link(interaction: discord.Interaction, player_tag: str):
    tag = player_tag.upper()
    linked_players[tag] = interaction.user.id
    save_links(linked_players)
    await interaction.response.send_message(
        f"✅ {interaction.user.mention} linked to **{tag}**",
        ephemeral=True
    )

# --------------------------
# Update Loop (War + Leaderboard)
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
        remaining = (end_dt - datetime.now(timezone.utc)).total_seconds()
        time_remaining = str(end_dt - datetime.now(timezone.utc)).split(".")[0]
    else:
        remaining = 0
        time_remaining = "N/A"

    # --------------------------
    # War Alerts
    # --------------------------

    pings = get_missing_attack_pings(clan.get("members", []), attacks_per_member)
    alert = None

    if state == "inWar":
        if not has_alert("start"):
            alert = f"{pings} ⚔️ War Started!" if pings else "⚔️ War Started!"
            log_alert("start")
        elif remaining <= 43200 and not has_alert("12h"):
            alert = f"{pings} ⏳ 12 hours remaining!" if pings else "⏳ 12 hours remaining!"
            log_alert("12h")
        elif remaining <= 3600 and not has_alert("1h"):
            alert = f"{pings} 🚨 1 hour left!" if pings else "🚨 1 hour left!"
            log_alert("1h")
    elif state == "warEnded":
        if not has_alert("end"):
            alert = "🏁 War Ended!"
            log_alert("end")
            reset_alerts()

    # --------------------------
    # Build War Embed
    # --------------------------

    members_data = []
    total_attacks = 0
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
        warn = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""
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
    embed.set_footer(text="AMA Bot • Auto Updates")

    channel = bot.get_channel(WAR_CHANNEL_ID)
    if channel:
        mid = get_saved_message(WAR_MESSAGE_FILE)
        try:
            if mid:
                msg = await channel.fetch_message(mid)
                await msg.edit(content=alert if alert else None, embed=embed)
            else:
                msg = await channel.send(content=alert if alert else None, embed=embed)
                save_message(WAR_MESSAGE_FILE, msg.id)
        except:
            msg = await channel.send(content=alert if alert else None, embed=embed)
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
    print("Slash commands synced")
    update_loop.start()

bot.run(DISCORD_TOKEN)