import os
import json
import requests
from datetime import datetime

CLAN_TAG = os.getenv("CLAN_TAG", "#2CYV200G")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "1477449787631603763")
API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

DATA_FILE = "monthly_data.json"
MESSAGE_ID_FILE = "monthly_leaderboard_id.txt"

month_key = datetime.now().strftime("%Y-%m")

# --- Fetch clan members ---
headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
encoded_tag = CLAN_TAG.replace("#", "%23")
url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    members_data = response.json().get("items", [])
except requests.exceptions.RequestException as e:
    print(f"❌ Error fetching clan members: {e}")
    members_data = []

# --- Load monthly data ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE) as f:
        monthly_data = json.load(f)
else:
    monthly_data = {}

if month_key not in monthly_data:
    monthly_data[month_key] = {}

month_stats = monthly_data[month_key]

# --- Build leaderboard ---
leaderboard = []

for member in members_data:
    name = member.get("name", "Unknown")
    donations = member.get("donations", 0)
    stars = month_stats.get(name, {}).get("stars", 0)
    combined = donations + stars

    leaderboard.append({
        "name": name,
        "donations": donations,
        "stars": stars,
        "combined": combined
    })

leaderboard.sort(key=lambda x: x["combined"], reverse=True)

# --- Save updated monthly data ---
for member in members_data:
    name = member.get("name", "Unknown")
    if name not in monthly_data[month_key]:
        monthly_data[month_key][name] = {}
    monthly_data[month_key][name]["stars"] = monthly_data[month_key][name].get("stars", 0)

with open(DATA_FILE, "w") as f:
    json.dump(monthly_data, f, indent=4)

# --- Build embed ---
description = ""
for i, player in enumerate(leaderboard[:15], start=1):
    description += (
        f"**{i}. {player['name']}**\n"
        f"⭐ {player['stars']} | 🎁 {player['donations']} | 🔥 {player['combined']}\n\n"
    )

embed = {
    "title": "🏆 AMA Monthly Gold Pass Leaderboard",
    "description": description.strip(),
    "color": 0xFFD700,
    "footer": {"text": f"Updates Daily • Month: {month_key}"}
}

payload = {"embeds": [embed]}
discord_headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}

# --- Handle dynamic Discord message ID ---
if os.path.exists(MESSAGE_ID_FILE):
    with open(MESSAGE_ID_FILE) as f:
        message_id = f.read().strip()
else:
    message_id = None

base_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"

if message_id:
    r = requests.patch(f"{base_url}/{message_id}", headers=discord_headers, json=payload)
    if r.status_code != 200:
        message_id = None

if not message_id:
    r = requests.post(base_url, headers=discord_headers, json=payload)
    if r.status_code == 200:
        new_id = r.json()["id"]
        with open(MESSAGE_ID_FILE, "w") as f:
            f.write(new_id)
        print("✅ Discord leaderboard posted successfully!")
else:
    print("✅ Discord leaderboard updated successfully!")