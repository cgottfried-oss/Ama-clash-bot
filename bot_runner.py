import os
import json
import time
import requests
from datetime import datetime, timezone

# -------------------------
# ENV VARIABLES
# -------------------------

CLAN_TAG = os.getenv("CLAN_TAG")
COC_API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

WAR_CHANNEL_ID = os.getenv("DISCORD_WAR_CHANNEL_ID")
LEADERBOARD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

WAR_ROLE_ID = os.getenv("DISCORD_WAR_ROLE_ID")

headers = {
    "Authorization": f"Bearer {COC_API_KEY}",
    "Accept": "application/json"
}

discord_headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

encoded_clan_tag = CLAN_TAG.replace("#", "%23")

# -------------------------
# FILES
# -------------------------

WAR_MESSAGE_FILE = "war_message_id.txt"
LEADERBOARD_MESSAGE_FILE = "leaderboard_message_id.txt"
WAR_STATE_FILE = "war_state.txt"
MONTHLY_DATA_FILE = "monthly_data.json"


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

    if previous_state != state:
        write_file(WAR_STATE_FILE, state)
        state_changed = True
    else:
        state_changed = False

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    team_size = war.get("teamSize", 0)
    attacks_per_member = war.get("attacksPerMember", 2)

    members = clan.get("members", [])

    members_data = []

    for m in members:

        name = m.get("name")
        attacks = m.get("attacks", [])

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        members_data.append({
            "name": name,
            "attacks": len(attacks),
            "stars": stars,
            "destruction": destruction
        })

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

    attack_lines = []

    for m in members_data:

        warning = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""

        line = f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} attacks • {m['stars']}⭐ • {m['destruction']}%{warning}"

        attack_lines.append(line)

    embed = {
        "title": f"⚔️ {clan.get('name')} vs {opponent.get('name')}",
        "description": f"State: **{state}**",
        "color": 0x2ECC71,
        "fields": [
            {
                "name": "Attack Tracker",
                "value": "\n\n".join(attack_lines) if attack_lines else "No attacks yet",
                "inline": False
            }
        ]
    }

    payload = {"embeds": [embed]}

    message_id = read_file(WAR_MESSAGE_FILE)

    url_base = f"https://discord.com/api/v10/channels/{WAR_CHANNEL_ID}/messages"

    if message_id:

        r = requests.patch(
            f"{url_base}/{message_id}",
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 404:
            message_id = None

    if not message_id:

        r = requests.post(
            url_base,
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 200:
            write_file(WAR_MESSAGE_FILE, r.json()["id"])

    # ---- WAR ALERTS ----

    if state_changed:

        if state == "inWar":

            alert = f"<@&{WAR_ROLE_ID}> ⚔️ War has started!"

        elif state == "warEnded":

            alert = f"<@&{WAR_ROLE_ID}> 🏁 War has ended!"

        else:
            alert = None

        if alert:

            requests.post(
                url_base,
                headers=discord_headers,
                json={"content": alert}
            )


# -------------------------
# MONTHLY LEADERBOARD
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

    for i, p in enumerate(leaderboard[:15], start=1):

        description += (
            f"**{i}. {p['name']}**\n"
            f"⭐ {p['stars']} | 🎁 {p['donations']} | 🔥 {p['combined']}\n\n"
        )

    embed = {
        "title": "🏆 AMA Monthly Gold Pass Leaderboard",
        "description": description.strip(),
        "color": 0xFFD700
    }

    payload = {"embeds": [embed]}

    message_id = read_file(LEADERBOARD_MESSAGE_FILE)

    url_base = f"https://discord.com/api/v10/channels/{LEADERBOARD_CHANNEL_ID}/messages"

    if message_id:

        r = requests.patch(
            f"{url_base}/{message_id}",
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 404:
            message_id = None

    if not message_id:

        r = requests.post(
            url_base,
            headers=discord_headers,
            json=payload
        )

        if r.status_code == 200:
            write_file(LEADERBOARD_MESSAGE_FILE, r.json()["id"])

    print("✅ Leaderboard refreshed")


# -------------------------
# MAIN LOOP
# -------------------------

print("AMA BOT RUNNER STARTED")

while True:

    try:
        update_war()
    except Exception as e:
        print("War error:", e)

    try:
        update_leaderboard()
    except Exception as e:
        print("Leaderboard error:", e)

    time.sleep(300)