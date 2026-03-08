import requests
import json
import os
import time
from datetime import datetime, timezone

API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CLAN_TAG = "#2CYV200G"
CHANNEL_ID = "1477452543604031631"
WAR_ROLE_ID = "1477540692321501287"

MESSAGE_ID_FILE = "war_message_id.txt"
ALERT_LOG_FILE = "war_alerts_log.txt"
WAR_ID_FILE = "war_id.txt"

CLAN_LOGO_URL = "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6FC08294-FD45.jpg"


def get_saved_message_id():
    if os.path.exists(MESSAGE_ID_FILE):
        with open(MESSAGE_ID_FILE) as f:
            return f.read().strip()
    return None


def save_message_id(message_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        f.write(message_id)


def get_saved_war_id():
    if os.path.exists(WAR_ID_FILE):
        with open(WAR_ID_FILE) as f:
            return f.read().strip()
    return None


def save_war_id(war_id):
    with open(WAR_ID_FILE, "w") as f:
        f.write(war_id)


def has_alert_fired(alert):
    if not os.path.exists(ALERT_LOG_FILE):
        return False
    with open(ALERT_LOG_FILE) as f:
        return alert in f.read().splitlines()


def log_alert(alert):
    with open(ALERT_LOG_FILE, "a") as f:
        f.write(alert + "\n")


def reset_alerts():
    if os.path.exists(ALERT_LOG_FILE):
        os.remove(ALERT_LOG_FILE)


encoded_clan_tag = CLAN_TAG.replace("#", "%23")
war_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"

headers_api = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

headers_bot = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}


def update_war():

    try:
        response = requests.get(war_url, headers=headers_api)
        response.raise_for_status()
        war_data = response.json()
    except Exception as e:
        print("Error fetching war:", e)
        return

    state = war_data.get("state")
    clan = war_data.get("clan", {})
    opponent = war_data.get("opponent", {})

    team_size = war_data.get("teamSize", 0)
    attacks_per_member = war_data.get("attacksPerMember", 2)

    war_id = war_data.get("preparationStartTime")
    saved_war_id = get_saved_war_id()

    if saved_war_id != war_id:
        print("New war detected — resetting alerts")
        save_war_id(war_id)
        reset_alerts()

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

    alert_message = None

    if state == "inWar":

        if not has_alert_fired("war_start"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⚔️ War has STARTED! Use both attacks!"
            log_alert("war_start")

        elif remaining_seconds <= 43200 and not has_alert_fired("12_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⏳ 12 hours remaining!"
            log_alert("12_hour")

        elif remaining_seconds <= 3600 and not has_alert_fired("1_hour"):
            alert_message = f"<@&{WAR_ROLE_ID}> 🚨 1 HOUR LEFT! Finish attacks!"
            log_alert("1_hour")

    elif state == "warEnded":

        if not has_alert_fired("war_end"):
            alert_message = f"<@&{WAR_ROLE_ID}> 🏁 War has ended!"
            log_alert("war_end")

    members_data = []
    total_attacks = 0

    for member in clan.get("members", []):

        name = member.get("name", "Unknown")
        attacks = member.get("attacks", [])

        attack_count = len(attacks)
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        total_attacks += attack_count

        members_data.append({
            "name": name,
            "attacks": attack_count,
            "stars": stars,
            "destruction": destruction
        })

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

    medals = ["🥇", "🥈", "🥉"]

    top_performers = []
    member_lines = []

    for i, m in enumerate(members_data):

        if i < 3 and m["stars"] > 0:
            top_performers.append(f"{medals[i]} **{m['name']}**")

        warning = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""

        line = (
            f"**{m['name']}**\n"
            f"➤ {m['attacks']}/{attacks_per_member} attacks • "
            f"{m['stars']}⭐ • "
            f"{m['destruction']}%{warning}"
        )

        member_lines.append(line)

    members_field = "\n\n".join(member_lines)

    if not top_performers and members_data:
        for i in range(min(3, len(members_data))):
            top_performers.append(f"{medals[i]} **{members_data[i]['name']}**")

    total_possible = team_size * attacks_per_member

    embed = {
        "title": f"⚔️ {clan.get('name')} vs {opponent.get('name', 'Opponent')}",
        "description": (
            f"**State:** {state.upper()}\n"
            f"**Team Size:** {team_size}v{team_size}\n"
            f"**Time Remaining:** {time_remaining}\n\n"
            f"🔥 **Attacks Used:** {total_attacks}/{total_possible}\n"
            f"⭐ **Score:** {clan.get('stars',0)} — {opponent.get('stars',0)}"
        ),
        "color": 0x2ECC71 if clan.get("stars", 0) >= opponent.get("stars", 0) else 0xE74C3C,
        "thumbnail": {"url": clan.get("badgeUrls", {}).get("large", CLAN_LOGO_URL)},
        "fields": [
            {
                "name": "🥇 Top Performers",
                "value": "\n".join(top_performers) if top_performers else "No attacks yet",
                "inline": False
            },
            {
                "name": "⚔️ Attack Tracker",
                "value": members_field,
                "inline": False
            }
        ],
        "footer": {"text": "AMA Bot • Auto Updates"}
    }

    payload = {
        "content": alert_message if alert_message else "",
        "embeds": [embed],
        "allowed_mentions": {"roles": [WAR_ROLE_ID]}
    }

    base_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"

    message_id = get_saved_message_id()

    if message_id:

        r = requests.patch(
            f"{base_url}/{message_id}",
            headers=headers_bot,
            json=payload
        )

        if r.status_code != 200:
            message_id = None

    if not message_id:

        r = requests.post(
            base_url,
            headers=headers_bot,
            json=payload
        )

        if r.status_code == 200:
            save_message_id(r.json()["id"])


print("War tracker started")

while True:

    try:
        update_war()
    except Exception as e:
        print("Error:", e)

    time.sleep(300)