import requests
import json
import os

# -------------------------
# CONFIGURATION - FILL THESE
# -------------------------
API_KEY = os.getenv("COC_API_KEY")
CLAN_TAG = "#2CYV200G"
WEBHOOK_URL = "https://discord.com/api/webhooks/1477722188047061184/LqH27ciYrFW3wkXQMK-zJ2peGmw7gN7Vf5yUjeGdPlCS9QQI2k0dcBNgIJ458mGiuNts"
CLAN_LOGO_URL = "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6-FC08294-FD45.jpg"
# -------------------------

MESSAGE_ID_FILE = "clan_stats_message_id.txt"

# Encode clan tag
encoded_clan_tag = CLAN_TAG.replace("#", "%23")
clan_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

# Fetch clan data
try:
    response = requests.get(clan_url, headers=headers)
    response.raise_for_status()
    clan = response.json()
except requests.exceptions.RequestException as e:
    print("Error fetching clan info:", e)
    exit()

# -------------------------
# CALCULATE WIN PERCENTAGE
# -------------------------
wins = clan.get("warWins", 0)
losses = clan.get("warLosses", 0)
ties = clan.get("warTies", 0)

total_wars = wins + losses + ties
if total_wars > 0:
    win_percentage = round((wins / total_wars) * 100, 2)
else:
    win_percentage = 0

# AMA Color (Deep Blue)
AMA_COLOR = 0x1E90FF

# Fields
fields = [
    {
        "name": "Members",
        "value": str(clan.get("members", 0)) + " / " + 
str(clan.get("memberLimit", 50)),
        "inline": True
    },
    {
        "name": "War Record",
        "value": f"{wins}W - {losses}L - {ties}T",
        "inline": True
    },
    {
        "name": "Win Rate",
        "value": f"{win_percentage}%",
        "inline": True
    },
    {
        "name": "War Stars",
        "value": str(clan.get("warStars", 0)),
        "inline": True
    },
    {
        "name": "Required Trophies",
        "value": str(clan.get("requiredTrophies", 0)),
        "inline": True
    },
    {
        "name": "Location",
        "value": clan.get("location", {}).get("name", "Unknown"),
        "inline": True
    }
]

embed_payload = {
    "embeds": [
        {
            "title": f"{clan.get('name')} — Clan Performance",
            "description": f"Tag: {clan.get('tag')} | Level: {clan.get('clanLevel')}",
            "color": AMA_COLOR,
            "thumbnail": {"url": CLAN_LOGO_URL},
            "fields": fields,
            "footer": {"text": "AMA Allegiance • Auto Updated"}
        }
    ]
}

# -------------------------
# AUTO EDIT INSTEAD OF REPOST
# -------------------------

if os.path.exists(MESSAGE_ID_FILE):
    with open(MESSAGE_ID_FILE, "r") as f:
        message_id = f.read().strip()

    edit_url = WEBHOOK_URL + f"/messages/{message_id}"

    try:
        edit_response = requests.patch(edit_url, json=embed_payload)
        edit_response.raise_for_status()
        print("Clan stats message updated successfully!")
    except requests.exceptions.RequestException as e:
        print("Failed to edit message, sending new one:", e)
        os.remove(MESSAGE_ID_FILE)
else:
    try:
        send_response = requests.post(WEBHOOK_URL + "?wait=true", 
json=embed_payload)
        send_response.raise_for_status()
        message_data = send_response.json()
        message_id = message_data["id"]

        with open(MESSAGE_ID_FILE, "w") as f:
            f.write(message_id)

        print("Clan stats message posted and message ID saved!")
    except requests.exceptions.RequestException as e:
        print("Error sending embed:", e)
