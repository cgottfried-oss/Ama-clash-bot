from dotenv import load_dotenv
import requests
import json
import os
from datetime import datetime, timezone

load_dotenv()  # Loads variables from .env

try:
    ip = requests.get("https://api.ipify.org").text
    print(f"🌍 Server Public IP: {ip}")
except:
    print("Could not fetch server IP")

# -------------------------
# CONFIG
TEST_MODE = False
API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLAN_TAG = "#2CYV200G"
CHANNEL_ID = "1477452543604031631"  # #current-war
WAR_ROLE_ID = "1477540692321501287"
MESSAGE_ID_FILE = "war_message_id.txt"
ALERT_LOG_FILE = "war_alerts_log.txt"
CLAN_LOGO_URL = (
    "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6FC08294-FD45.jpg"
)
MONTHLY_DATA_FILE = "monthly_data.json"
# -------------------------


# --- Helpers ---
def get_saved_message_id():
    if os.path.exists(MESSAGE_ID_FILE):
        with open(MESSAGE_ID_FILE) as f:
            return f.read().strip()
    return None


def save_message_id(message_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        f.write(message_id)


def has_alert_fired(alert_name):
    if not os.path.exists(ALERT_LOG_FILE):
        return False
    with open(ALERT_LOG_FILE) as f:
        return alert_name in f.read().splitlines()


def log_alert(alert_name):
    with open(ALERT_LOG_FILE, "a") as f:
        f.write(alert_name + "\n")


# --- Fetch current war data ---
encoded_clan_tag = CLAN_TAG.replace("#", "%23")
war_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"
headers_api = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}

try:
    response = requests.get(war_url, headers=headers_api)
    response.raise_for_status()
    war_data = response.json()
except requests.exceptions.RequestException as e:
    print("Error fetching clan war data:", e)
    exit()

clan = war_data.get("clan", {})
opponent = war_data.get("opponent", {})
state = war_data.get("state", "N/A")
team_size = war_data.get("teamSize", "N/A")

# --- Calculate time remaining ---
end_time = war_data.get("endTime")
if end_time:
    end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(
        tzinfo=timezone.utc
    )
    now = datetime.now(timezone.utc)
    remaining_seconds = (end_dt - now).total_seconds()
    time_remaining_str = str(end_dt - now).split(".")[0]
else:
    remaining_seconds = 0
    time_remaining_str = "N/A"

# --- Determine alerts ---
alert_message = None
if TEST_MODE:
    alert_message = f"<@&{WAR_ROLE_ID}> ⚔️ War has STARTED Use bothattacks!"
    print("Simulating war start alert...")
else:
    if state == "inWar":
        if not has_alert_fired("war_start"):
            alert_message = f"<@&{WAR_ROLE_ID}> ⚔️ War has STARTED! Ueseboth attacks!"
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
            # Reset alerts for next war
            if os.path.exists(ALERT_LOG_FILE):
                os.remove(ALERT_LOG_FILE)

# --- Build advanced member attack info ---
members_data = []
total_attacks_used = 0
attacks_per_member = war_data.get("attacksPerMember", 2)

for member in clan.get("members", []):
    name = member.get("name", "Unknown")
    attacks = member.get("attacks", [])

    attack_count = len(attacks)
    stars = sum(a.get("stars", 0) for a in attacks)
    destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

    total_attacks_used += attack_count

    members_data.append(
        {
            "name": name,
            "attacks": attack_count,
            "stars": stars,
            "destruction": destruction,
        }
    )

# Sort by stars then destruction

members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

# Initialize display lists
top_performers = []
member_lines = []

medals = ["🥇", "🥈", "🥉"]

for index, m in enumerate(members_data):

    # Only add to top performers if they actually have stars
    if index < 3 and m["stars"] > 0:
        top_performers.append(f"{medals[index]} **{m['name']}**")

    warning = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""

    line = (
        f"**{m['name']}**\n"
        f"➤ {m['attacks']}/{attacks_per_member} attacks • "
        f"{m['stars']}⭐ • "
        f"{m['destruction']}%{warning}"
    )

    member_lines.append(line)

members_field = "\n\n".join(member_lines)

# If nobody has stars yet but attacks exist
if not top_performers and members_data:
    for i in range(min(3, len(members_data))):
        top_performers.append(f"{medals[i]} **{members_data[i]['name']}**")

# --- Build formatted member list ---
top_performers = []
member_lines = []

medals = ["🥇", "🥈", "🥉"]

for index, m in enumerate(members_data):

    # Only add to top performers if they actually have stars
    if index < 3 and m["stars"] > 0:
        top_performers.append(f"{medals[index]} **{m['name']}**")

    warning = " ⚠️" if m["attacks"] == 0 and state == "inWar" else ""

    line = (
        f"**{m['name']}**\n"
        f"➤ {m['attacks']}/{attacks_per_member} attacks • "
        f"{m['stars']}⭐ • "
        f"{m['destruction']}%{warning}"
    )

    member_lines.append(line)

members_field = "\n\n".join(member_lines)

# If nobody has stars yet but attacks exist
if not top_performers and members_data:
    for i in range(min(3, len(members_data))):
        name = members_data[i]["name"]
        medal = medals[i] if i < len(medals) else ""
        top_performers.append(f"{medal} **{name}**")

# --- Attack usage summary ---
total_possible_attacks = team_size * attacks_per_member
attack_summary = f"{total_attacks_used}/{total_possible_attacks}"

# --- Destruction comparison ---
clan_destruction = clan.get("destructionPercentage", 0)
opponent_destruction = opponent.get("destructionPercentage", 0)

destruction_compare = (
    f"🏰 **{clan.get('name')}** — {clan_destruction}%\n\n"
    f"⚔️ **{opponent.get('name', 'Opponent')}** — {opponent_destruction}%\n"
)

# --- Time remaining formatting ---
if remaining_seconds > 0:
    hours = int(remaining_seconds // 3600)
    minutes = int((remaining_seconds % 3600) // 60)
    time_remaining_str = f"{hours}h {minutes}m"
else:
    time_remaining_str = "Ended"

# --- Build upgraded embed ---
embed = {
    "title": f"⚔️ {clan.get('name')} vs {opponent.get('name', 'TBD')}",
    "description": (
        f"**State:** {state.upper()}\n"
        f"**Team Size:** {team_size}v{team_size}\n"
        f"**Time Remaining:** {time_remaining_str}\n\n"
        f"🔥 **Attacks Used:** {attack_summary}\n"
        f"⭐ **Score:** {clan.get('stars',0)} — {opponent.get('stars',0)}\n\u200b"
    ),
    "color": 0x2ECC71 if clan.get("stars", 0) >= opponent.get("stars", 0) else 0xE74C3C,
    "thumbnail": {"url": clan.get("badgeUrls", {}).get("large", CLAN_LOGO_URL)},
    "fields": [
        {
            "name": "__🥇 Top Performers__",
            "value": (
                ("\n\n".join(top_performers) + "\n\n\u200b")
                if top_performers
                else "No attacks yet\n\u200b"
            ),
            "inline": False,
        },
        {
            "name": "__📊 Destruction Comparison__",
            "value": destruction_compare + "\n\u200b",
            "inline": False,
        },
        {
            "name": "__⚔️ Attack Tracke__r",
            "value": members_field + "\n\u200b",
            "inline": False,
        },
    ],
    "footer": {"text": "AMA Bot • Auto Updates"},
}
payload = {
    "content": alert_message if alert_message else "",
    "embeds": [embed],
    "allowed_mentions": {"roles": [WAR_ROLE_ID]},
}
# --- Send/update embed via bot ---
base_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
headers_bot = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
message_id = get_saved_message_id()


def post_new_message():
    r = requests.post(base_url, headers=headers_bot, json=payload)
    if r.status_code == 200:
        new_id = r.json()["id"]
        save_message_id(new_id)
        print("War embed posted successfully!")
    else:
        print("Error posting embed:", r.status_code, r.text)


if message_id:
    patch_url = f"{base_url}/{message_id}"
    r = requests.patch(patch_url, headers=headers_bot, json=payload)
    if r.status_code == 200:
        print("War embed updated!")
    else:
        print("Saved message missing or invalid, posting new embed...")
        post_new_message()
else:
    post_new_message()
