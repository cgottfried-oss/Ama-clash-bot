from dotenv import load_dotenv
import os
import requests
import json
from datetime import datetime

# --- Load environment ---
load_dotenv()
CLAN_TAG = os.getenv("CLAN_TAG", "#2CYV200G")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "1477449787631603763")
MESSAGE_ID = os.getenv("DISCORD_MESSAGE_ID", "1478171448026857513")
API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

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
if os.path.exists("monthly_data.json"):
    with open("monthly_data.json") as f:
        monthly_data = json.load(f)
else:
    monthly_data = {}

month_stats = monthly_data.get(month_key, {})

# --- Build leaderboard ---
leaderboard = []
for member in members_data:
    name = member.get("name", "Unknown")
    donations = member.get("donations", 0)
    stars = month_stats.get(name, {}).get("stars", 0)
    combined = donations + stars

    leaderboard.append(
        {"name": name, "donations": donations, "stars": stars, "combined": combined}
    )

# --- Sort by combined score descending ---
leaderboard.sort(key=lambda x: x["combined"], reverse=True)

# --- Print leaderboard to terminal ---
print(f"\n🏆 AMA Monthly Gold Pass Leaderboard ({month_key})")
print("-" * 40)
for i, player in enumerate(leaderboard[:15], start=1):
    print(f"{i}. {player['name']}")
    print(
        f"   ⭐ Stars: {player['stars']} | 🎁 Donations: {player['donations']} | 🔥 Combined: {player['combined']}\n"
    )

# --- Build embed for Discord ---
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
    "footer": {"text": f"Updates Daily • Month: {month_key}"},
}

payload = {"embeds": [embed]}

discord_headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}

edit_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages/{MESSAGE_ID}"

# --- Send PATCH to Discord ---
try:
    r = requests.patch(edit_url, headers=discord_headers, json=payload)
    if r.status_code == 200:
        print("✅ Discord leaderboard updated successfully!\n")
    else:
        print(f"❌ Failed to update Discord: {r.status_code} - {r.text}\n")
except requests.exceptions.RequestException as e:
    print(f"❌ Error sending request to Discord: {e}\n")
