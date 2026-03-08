import os
import json
import requests
import time
from datetime import datetime, timezone, timedelta

# ----------------------------
# Environment / Config
# ----------------------------
CLAN_TAG = os.getenv("CLAN_TAG", "#2CYV200G")

# War tracker
WAR_CHANNEL_ID = os.getenv("DISCORD_WAR_CHANNEL_ID", "1477452543604031631")
WAR_ROLE_ID = os.getenv("DISCORD_WAR_ROLE_ID", "1477540692321501287")

# Monthly leaderboard
LEADERBOARD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "1477449787631603763")
UPDATE_HOUR = 0  # Daily update hour in UTC

API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Files
WAR_MESSAGE_FILE = "war_message_id.txt"
WAR_ALERT_FILE = "war_alerts_log.txt"
WAR_ID_FILE = "war_id.txt"
LEADERBOARD_MESSAGE_FILE = "monthly_leaderboard_id.txt"
MONTHLY_DATA_FILE = "monthly_data.json"

CLAN_LOGO_URL = "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6FC08294-FD45.jpg"

# ----------------------------
# Helper Functions
# ----------------------------
def read_file(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            return f.read().strip()
    return None

def write_file(file_path, content):
    with open(file_path, "w") as f:
        f.write(content)

def has_alert(alert_name):
    if not os.path.exists(WAR_ALERT_FILE):
        return False
    with open(WAR_ALERT_FILE) as f:
        return alert_name in f.read().splitlines()

def log_alert(alert_name):
    with open(WAR_ALERT_FILE, "a") as f:
        f.write(alert_name + "\n")

def reset_alerts():
    if os.path.exists(WAR_ALERT_FILE):
        os.remove(WAR_ALERT_FILE)

# ----------------------------
# War Tracker
# ----------------------------
def update_war():
    encoded_tag = CLAN_TAG.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    headers_api = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers_api)
        response.raise_for_status()
        war_data = response.json()
    except Exception as e:
        print("❌ Error fetching war:", e)
        return

    state = war_data.get("state")
    clan = war_data.get("clan", {})
    opponent = war_data.get("opponent", {})
    team_size = war_data.get("teamSize", 0)
    attacks_per_member = war_data.get("attacksPerMember", 2)
    war_id = war_data.get("preparationStartTime")
    saved_war_id = read_file(WAR_ID_FILE)

    if saved_war_id != war_id:
        print("New war detected — resetting alerts")
        write_file(WAR_ID_FILE, war_id or "")
        reset_alerts()

    # Time remaining
    end_time = war_data.get("endTime")
    remaining_seconds = 0
    time_remaining = "N/A"
    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        remaining_seconds = (end_dt - now).total_seconds()
        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)
        time_remaining = f"{hours}h {minutes}m" if remaining_seconds > 0 else "Ended"

    # Alerts
    alert_message = None
    if state == "inWar":
        if not has_alert("war_start"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⚔️ War has STARTED! Use both attacks!"
            log_alert("war_start")
        elif remaining_seconds <= 43200 and not has_alert("12_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⏳ 12 hours remaining!"
            log_alert("12_hour")
        elif remaining_seconds <= 3600 and not has_alert("1_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> 🚨 1 HOUR LEFT! Finish attacks!"
            log_alert("1_hour")
    elif state == "warEnded" and not has_alert("war_end"):
        alert_message = f"<@&{WAR_ROLE_ID}> 🏁 War has ended!"
        log_alert("war_end")

    # Members
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

    total_possible = team_size * attacks_per_member

    # Build embed
    embed = {
        "title": f"⚔️ {clan.get('name')} vs {opponent.get('name', 'Opponent')}",
        "description": f"**State:** {state.upper()}\n**Team Size:** {team_size}v{team_size}\n**Time Remaining:** {time_remaining}\n\n🔥 **Attacks Used:** {total_attacks_used}/{total_possible}\n⭐ **Score:** {clan.get('stars',0)} — {opponent.get('stars',0)}",
        "color": 0x2ECC71 if clan.get("stars", 0) >= opponent.get("stars", 0) else 0xE74C3C,
        "thumbnail": {"url": clan.get("badgeUrls", {}).get("large", CLAN_LOGO_URL)},
        "fields": [
            {"name": "🥇 Top Performers", "value": "\n".join(top_performers) or "No attacks yet", "inline": False},
            {"name": "⚔️ Attack Tracker", "value": members_field, "inline": False}
        ],
        "footer": {"text": "AMA Bot • Auto Updates"}
    }

    payload = {"content": alert_message or "", "embeds": [embed], "allowed_mentions": {"roles": [WAR_ROLE_ID]}}
    base_url = f"https://discord.com/api/v10/channels/{WAR_CHANNEL_ID}/messages"
    message_id = read_file(WAR_MESSAGE_FILE)

    if message_id:
        r = requests.patch(base_url + "/" + message_id, headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}, json=payload)
        if r.status_code == 404:
            message_id = None  # first-time missing message, silent
        elif r.status_code != 200:
            print(f"❌ War PATCH error {r.status_code}: {r.text}")

    if not message_id:
        r = requests.post(base_url, headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}, json=payload)
        if r.status_code == 200:
            write_file(WAR_MESSAGE_FILE, r.json()["id"])

# ----------------------------
# Monthly Leaderboard
# ----------------------------
def update_leaderboard():
    month_key = datetime.now().strftime("%Y-%m")
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    encoded_tag = CLAN_TAG.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        members_data = response.json().get("items", [])
    except:
        members_data = []

    # Load monthly data
    if os.path.exists(MONTHLY_DATA_FILE):
        with open(MONTHLY_DATA_FILE) as f:
            monthly_data = json.load(f)
    else:
        monthly_data = {}

    if month_key not in monthly_data:
        monthly_data[month_key] = {}

    month_stats = monthly_data[month_key]
    leaderboard = []

    for member in members_data:
        name = member.get("name", "Unknown")
        donations = member.get("donations", 0)
        stars = month_stats.get(name, {}).get("stars", 0)
        combined = donations + stars
        leaderboard.append({"name": name, "donations": donations, "stars": stars, "combined": combined})

    leaderboard.sort(key=lambda x: x["combined"], reverse=True)

    # Save monthly data
    for member in members_data:
        name = member.get("name", "Unknown")
        if name not in monthly_data[month_key]:
            monthly_data[month_key][name] = {}
        monthly_data[month_key][name]["stars"] = monthly_data[month_key][name].get("stars", 0)

    with open(MONTHLY_DATA_FILE, "w") as f:
        json.dump(monthly_data, f, indent=4)

    # Build embed
    description = ""
    for i, player in enumerate(leaderboard[:15], start=1):
        description += f"**{i}. {player['name']}**\n⭐ {player['stars']} | 🛡️ {player['donations']} | 🔥 {player['combined']}\n\n"

    embed = {"title": "🏆 AMA Monthly Gold Pass Leaderboard", "description": description.strip(),
             "color": 0xFFD700, "footer": {"text": f"Updates Daily • Month: {month_key}"}}

    payload = {"embeds": [embed]}
    base_url = f"https://discord.com/api/v10/channels/{LEADERBOARD_CHANNEL_ID}/messages"
    message_id = read_file(LEADERBOARD_MESSAGE_FILE)

    if message_id:
        r = requests.patch(base_url + "/" + message_id, headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}, json=payload)
        if r.status_code == 404:
            message_id = None  # first-time missing message, silent
        elif r.status_code != 200:
            print(f"❌ Leaderboard PATCH error {r.status_code}: {r.text}")

    if not message_id:
        r = requests.post(base_url, headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}, json=payload)
        if r.status_code == 200:
            write_file(LEADERBOARD_MESSAGE_FILE, r.json()["id"])

# ----------------------------
# Main Loop
# ----------------------------
print("Bot Runner Started")

next_leaderboard_run = None

while True:
    try:
        # Run war tracker every 5 minutes
        update_war()
    except Exception as e:
        print("❌ War tracker error:", e)

    # Check if we need to run leaderboard
    now = datetime.utcnow()
    if not next_leaderboard_run:
        next_leaderboard_run = now.replace(hour=UPDATE_HOUR, minute=0, second=0, microsecond=0)
        if next_leaderboard_run <= now:
            next_leaderboard_run += timedelta(days=1)

    if now >= next_leaderboard_run:
        try:
            update_leaderboard()
            print("✅ Daily leaderboard updated")
        except Exception as e:
            print("❌ Leaderboard error:", e)
        next_leaderboard_run += timedelta(days=1)

    time.sleep(300)  # 5-minute interval