import os
import json
import time
import asyncio
import requests
from datetime import datetime, timezone
from discord import Client, Intents, Embed
from dotenv import load_dotenv

# --- Load env variables ---
load_dotenv()

def get_env_var(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"⚠️ Environment variable {name} not set!")
    return value

DISCORD_TOKEN = get_env_var("DISCORD_BOT_TOKEN")
API_KEY = get_env_var("CLASH_API_KEY")
CLAN_TAG = get_env_var("CLAN_TAG")
WAR_ROLE_ID = get_env_var("WAR_ROLE_ID")
CURRENT_WAR_CHANNEL_ID = get_env_var("WAR_CHANNEL_ID")
LEADERBOARD_CHANNEL_ID = get_env_var("LEADERBOARD_CHANNEL_ID")

# --- Persistent storage (Coolify volume mount) ---
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

ALERT_LOG_FILE = os.path.join(DATA_DIR, "war_alerts_log.txt")
CURRENT_WAR_MESSAGE_ID_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LINKED_ACCOUNTS_FILE = os.path.join(DATA_DIR, "linked_accounts.json")

if not os.path.exists(LINKED_ACCOUNTS_FILE):
    with open(LINKED_ACCOUNTS_FILE, "w") as f:
        json.dump({}, f)

# --- Discord client ---
intents = Intents.default()
intents.messages = True
intents.message_content = True

bot = Client(intents=intents)

# --- Helpers for persistent files ---
def get_saved_message_id():
    if os.path.exists(CURRENT_WAR_MESSAGE_ID_FILE):
        with open(CURRENT_WAR_MESSAGE_ID_FILE) as f:
            return f.read().strip()
    return None

def save_message_id(message_id):
    with open(CURRENT_WAR_MESSAGE_ID_FILE, "w") as f:
        f.write(message_id)

def has_alert_fired(alert_name):
    if not os.path.exists(ALERT_LOG_FILE):
        return False
    with open(ALERT_LOG_FILE) as f:
        return alert_name in f.read().splitlines()

def log_alert(alert_name):
    with open(ALERT_LOG_FILE, "a") as f:
        f.write(alert_name + "\n")

def reset_alerts():
    if os.path.exists(ALERT_LOG_FILE):
        os.remove(ALERT_LOG_FILE)
        print("New war detected — resetting alerts")

# --- Helper to fetch clan data ---
def fetch_clan_members():
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    encoded_tag = CLAN_TAG.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("items", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching clan members: {e}")
        return []

# --- War embed updater ---
async def update_current_war():
    headers_api = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    encoded_tag = CLAN_TAG.replace("#", "%23")
    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"

    try:
        response = requests.get(war_url, headers=headers_api)
        response.raise_for_status()
        war_data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error fetching clan war data:", e)
        return

    state = war_data.get("state", "N/A")
    clan = war_data.get("clan", {})
    opponent = war_data.get("opponent", {})
    team_size = war_data.get("teamSize", 0)
    attacks_per_member = war_data.get("attacksPerMember", 2)
    end_time = war_data.get("endTime")

    # Time remaining
    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        remaining_seconds = (end_dt - now).total_seconds()
        time_remaining_str = str(end_dt - now).split(".")[0]
    else:
        remaining_seconds = 0
        time_remaining_str = "Ended"

    # --- Determine alerts ---
    alert_message = None
    if state == "inWar":
        if not has_alert_fired("war_start"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⚔️ War has STARTED! Use both attacks!"
            log_alert("war_start")
        elif remaining_seconds <= 12 * 3600 and not has_alert_fired("12_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⏳ 12 hours remaining!"
            log_alert("12_hour")
        elif remaining_seconds <= 3600 and not has_alert_fired("1_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> 🚨 1 HOUR LEFT! Finish attacks!"
            log_alert("1_hour")
    elif state == "warEnded":
        if not has_alert_fired("war_end"):
            alert_message = f"<@&{WAR_ROLE_ID}> 🏁 War has ended!"
            log_alert("war_end")
            reset_alerts()

    # --- Build embed ---
    members_data = []
    total_attacks_used = 0
    for member in clan.get("members", []):
        name = member.get("name", "Unknown")
        attacks = member.get("attacks", [])
        attack_count = len(attacks)
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        total_attacks_used += attack_count
        members_data.append({"name": name, "attacks": attack_count, "stars": stars, "destruction": destruction})

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)
    medals = ["🥇", "🥈", "🥉"]

    top_performers = []
    member_lines = []
    for i, m in enumerate(members_data):
        if i < 3 and m["stars"] > 0:
            top_performers.append(f"{medals[i]} **{m['name']}**")
        warning = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""
        line = f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} attacks • {m['stars']}⭐ • {m['destruction']}%{warning}"
        member_lines.append(line)

    members_field = "\n\n".join(member_lines)
    if not top_performers and members_data:
        for i in range(min(3, len(members_data))):
            top_performers.append(f"{medals[i]} **{members_data[i]['name']}**")

    total_possible_attacks = team_size * attacks_per_member
    attack_summary = f"{total_attacks_used}/{total_possible_attacks}"

    clan_destruction = clan.get("destructionPercentage", 0)
    opponent_destruction = opponent.get("destructionPercentage", 0)
    destruction_compare = f"🏰 **{clan.get('name')}** — {clan_destruction}%\n\n⚔️ **{opponent.get('name', 'Opponent')}** — {opponent_destruction}%\n"

    embed = Embed(
        title=f"⚔️ {clan.get('name')} vs {opponent.get('name', 'TBD')}",
        description=(
            f"**State:** {state.upper()}\n"
            f"**Team Size:** {team_size}v{team_size}\n"
            f"**Time Remaining:** {time_remaining_str}\n\n"
            f"🔥 **Attacks Used:** {attack_summary}\n"
            f"⭐ **Score:** {clan.get('stars',0)} — {opponent.get('stars',0)}"
        ),
        color=0x2ECC71 if clan.get("stars", 0) >= opponent.get("stars", 0) else 0xE74C3C
    )
    embed.add_field(name="__🥇 Top Performers__", value="\n\n".join(top_performers) if top_performers else "No attacks yet", inline=False)
    embed.add_field(name="__📊 Destruction Comparison__", value=destruction_compare, inline=False)
    embed.add_field(name="__⚔️ Attack Tracker__", value=members_field, inline=False)
    embed.set_footer(text="AMA Bot • Auto Updates")

    channel = await bot.fetch_channel(int(CURRENT_WAR_CHANNEL_ID))
    message_id = get_saved_message_id()

    try:
        if message_id:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(content=alert_message or "", embed=embed)
        else:
            msg = await channel.send(content=alert_message or "", embed=embed)
            save_message_id(msg.id)
    except:
        # If fetching fails, post a new message
        msg = await channel.send(content=alert_message or "", embed=embed)
        save_message_id(msg.id)

# --- Main bot loop ---
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    while True:
        await update_current_war()
        # Call monthly leaderboard here if needed
        subprocess.run(["python", "monthly_leaderboard.py"])
        await asyncio.sleep(600)  # 10 minutes

bot.run(DISCORD_TOKEN)