import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta

# -------------------------
# ENV VARIABLES
# -------------------------

CLAN_TAG = os.getenv("CLAN_TAG")
COC_API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

WAR_CHANNEL_ID = os.getenv("DISCORD_WAR_CHANNEL_ID")
LEADERBOARD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
GOLD_PASS_CHANNEL_ID = os.getenv("GOLD_PASS_CHANNEL_ID")

WAR_ROLE_ID = os.getenv("DISCORD_WAR_ROLE_ID")

encoded_clan_tag = CLAN_TAG.replace("#", "%23")

headers = {
    "Authorization": f"Bearer {COC_API_KEY}",
    "Accept": "application/json"
}

discord_headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

# -------------------------
# FILE STORAGE
# -------------------------

WAR_MESSAGE_FILE = "war_message_id.txt"
LEADERBOARD_MESSAGE_FILE = "leaderboard_message_id.txt"
WAR_STATE_FILE = "war_state.txt"
MONTHLY_DATA_FILE = "monthly_data.json"
REMINDER_LOG = "reminder_log.txt"

# -------------------------
# FILE HELPERS
# -------------------------

def read_file(path):
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return None

def write_file(path, value):
    with open(path, "w") as f:
        f.write(str(value))

def reminder_sent(tag):
    if not os.path.exists(REMINDER_LOG):
        return False
    with open(REMINDER_LOG) as f:
        return tag in f.read()

def log_reminder(tag):
    with open(REMINDER_LOG, "a") as f:
        f.write(tag + "\n")

# -------------------------
# WAR TRACKER
# -------------------------

def update_war():

    url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        war = r.json()
    except:
        print("❌ Failed to fetch war data")
        return

    state = war.get("state")
    previous_state = read_file(WAR_STATE_FILE)

    state_changed = previous_state != state

    if state_changed:
        write_file(WAR_STATE_FILE, state)

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    team_size = war.get("teamSize", 0)
    attacks_per_member = war.get("attacksPerMember", 2)

    members = clan.get("members", [])

    members_data = []
    total_attacks_used = 0

    for m in members:

        name = m.get("name")
        attacks = m.get("attacks", [])

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        attack_count = len(attacks)
        total_attacks_used += attack_count

        members_data.append({
            "name": name,
            "attacks": attack_count,
            "stars": stars,
            "destruction": destruction
        })

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

    # -------------------------
    # TOP PERFORMERS
    # -------------------------

    medals = ["🥇", "🥈", "🥉"]
    top_lines = []

    for i, p in enumerate(members_data[:3]):
        top_lines.append(f"{medals[i]} {p['name']} — {p['stars']}⭐")

    # -------------------------
    # ATTACK TRACKER
    # -------------------------

    attack_lines = []
    missing_attacks = []

    for m in members_data:

        if m["attacks"] == 0 and state == "inWar":
            attack_lines.append(f"{m['name']} • 0/{attacks_per_member} ⚠️")
            missing_attacks.append(m["name"])
        else:
            attack_lines.append(
                f"{m['name']} • {m['attacks']}/{attacks_per_member} ⚔️ • {m['stars']}⭐ • {m['destruction']}%"
            )

    # -------------------------
    # TIME REMAINING
    # -------------------------

    remaining_seconds = None
    time_remaining = "Unknown"

    end_time = war.get("endTime")

    if end_time:

        end = datetime.strptime(
            end_time, "%Y%m%dT%H%M%S.000Z"
        ).replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        remaining_seconds = (end - now).total_seconds()

        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)

        if remaining_seconds > 0:
            time_remaining = f"{hours}h {minutes}m"
        else:
            time_remaining = "Ended"

    # -------------------------
    # BUILD EMBED
    # -------------------------

    embed = {

        "title": f"⚔️ {clan.get('name')} vs {opponent.get('name')}",

        "description":
            f"**State:** {state.upper()}\n"
            f"**Team Size:** {team_size}v{team_size}\n"
            f"**Time Remaining:** {time_remaining}\n"
            f"**Attacks Used:** {total_attacks_used}/{team_size * attacks_per_member}\n"
            f"**Score:** {clan.get('stars',0)} ⭐ — {opponent.get('stars',0)} ⭐",

        "color": 0x2ECC71,

        "fields": [

            {
                "name": "🥇 Top Performers",
                "value": "\n".join(top_lines) if top_lines else "No attacks yet",
                "inline": False
            },

            {
                "name": "⚔️ Attack Tracker",
                "value": "\n".join(attack_lines),
                "inline": False
            }

        ]
    }

    payload = {"embeds": [embed]}

    base_url = f"https://discord.com/api/v10/channels/{WAR_CHANNEL_ID}/messages"

    message_id = read_file(WAR_MESSAGE_FILE)

    if message_id:

        r = requests.patch(
            f"{base_url}/{message_id}",
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 404:
            message_id = None

    if not message_id:

        r = requests.post(
            base_url,
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 200:
            write_file(WAR_MESSAGE_FILE, r.json()["id"])

    # -------------------------
    # WAR START / END ALERTS
    # -------------------------

    if state_changed:

        if state == "inWar":

            msg = f"<@&{WAR_ROLE_ID}> ⚔️ **War has started!** Use both attacks!"

        elif state == "warEnded":

            msg = f"<@&{WAR_ROLE_ID}> 🏁 **War has ended!**"

        else:
            msg = None

        if msg:
            requests.post(base_url, headers=discord_headers, json={"content": msg})

    # -------------------------
    # WAR REMINDERS
    # -------------------------

    if remaining_seconds:

        if remaining_seconds < 43200 and not reminder_sent("12h"):

            if missing_attacks:

                msg = (
                    f"<@&{WAR_ROLE_ID}> ⏳ **12 HOURS LEFT**\n"
                    "Players with attacks remaining:\n"
                    + "\n".join(missing_attacks)
                )

                requests.post(base_url, headers=discord_headers, json={"content": msg})

                log_reminder("12h")

        if remaining_seconds < 3600 and not reminder_sent("1h"):

            if missing_attacks:

                msg = (
                    f"<@&{WAR_ROLE_ID}> 🚨 **1 HOUR LEFT**\n"
                    "Finish your attacks:\n"
                    + "\n".join(missing_attacks)
                )

                requests.post(base_url, headers=discord_headers, json={"content": msg})

                log_reminder("1h")


# -------------------------
# LEADERBOARD
# -------------------------

def update_leaderboard():

    url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/members"

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        members = r.json().get("items", [])
    except:
        print("❌ Failed to fetch clan members")
        return

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")

    if os.path.exists(MONTHLY_DATA_FILE):
        with open(MONTHLY_DATA_FILE) as f:
            monthly_data = json.load(f)
    else:
        monthly_data = {}

    if month_key not in monthly_data:
        monthly_data[month_key] = {}

    leaderboard = []

    for m in members:

        name = m.get("name")
        donations = m.get("donations", 0)

        stars = monthly_data[month_key].get(name, {}).get("stars", 0)

        combined = stars + donations

        leaderboard.append({
            "name": name,
            "stars": stars,
            "donations": donations,
            "combined": combined
        })

    leaderboard.sort(key=lambda x: x["combined"], reverse=True)

    description = ""

    medals = ["🥇", "🥈", "🥉"]

    for i, p in enumerate(leaderboard[:15]):

        medal = medals[i] if i < 3 else ""

        description += (
            f"**{medal} {i+1}. {p['name']}**\n"
            f"⭐ {p['stars']} | 🎁 {p['donations']} | 🔥 {p['combined']}\n\n"
        )

    embed = {
        "title": "🏆 AMA Monthly Gold Pass Leaderboard",
        "description": description.strip(),
        "color": 0xFFD700
    }

    payload = {"embeds": [embed]}

    base_url = f"https://discord.com/api/v10/channels/{LEADERBOARD_CHANNEL_ID}/messages"

    message_id = read_file(LEADERBOARD_MESSAGE_FILE)

    if message_id:

        r = requests.patch(
            f"{base_url}/{message_id}",
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 404:
            message_id = None

    if not message_id:

        r = requests.post(
            base_url,
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 200:
            write_file(LEADERBOARD_MESSAGE_FILE, r.json()["id"])

    print("✅ Leaderboard refreshed")


# -------------------------
# GOLD PASS WINNER
# -------------------------

def check_month_end():

    today = datetime.now(timezone.utc)

    if today.day != 1:
        return

    if not os.path.exists(MONTHLY_DATA_FILE):
        return

    with open(MONTHLY_DATA_FILE) as f:
        data = json.load(f)

    previous_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    if previous_month not in data:
        return

    players = data[previous_month]

    winner = max(
        players.items(),
        key=lambda x: x[1].get("stars",0) + x[1].get("donations",0)
    )

    name = winner[0]
    stats = winner[1]

    total = stats.get("stars",0) + stats.get("donations",0)

    message = (
        f"🏆 **Gold Pass Winner — {previous_month}**\n\n"
        f"🥇 {name}\n"
        f"⭐ Stars: {stats.get('stars',0)}\n"
        f"🎁 Donations: {stats.get('donations',0)}\n"
        f"🔥 Total Score: {total}"
    )

    url = f"https://discord.com/api/v10/channels/{GOLD_PASS_CHANNEL_ID}/messages"

    requests.post(url, headers=discord_headers, json={"content": message})


# -------------------------
# MAIN LOOP
# -------------------------

print("🚀 AMA BOT RUNNER STARTED")

while True:

    try:
        update_war()
    except Exception as e:
        print("War error:", e)

    try:
        update_leaderboard()
    except Exception as e:
        print("Leaderboard error:", e)

    try:
        check_month_end()
    except Exception as e:
        print("Gold pass error:", e)

    time.sleep(300)