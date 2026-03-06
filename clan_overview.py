import requests
import json
import os

# -------------------------
# CONFIG
API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLAN_TAG = "#2CYV200G"
CHANNEL_ID = "1477449787631603763"  # #clan-overview
CLAN_LOGO_URL = "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6FC08294-FD45.jpg"
MONTHLY_DATA_FILE = "monthly_data.json"
MESSAGE_ID_FILE = "clan_overview_message_id.txt"
# -------------------------

# --- Helper functions ---
def get_saved_message_id():
    if os.path.exists(MESSAGE_ID_FILE):
        with open(MESSAGE_ID_FILE) as f:
            return f.read().strip()
    return None

def save_message_id(message_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        f.write(message_id)

# --- Load monthly war data ---
if os.path.exists(MONTHLY_DATA_FILE):
    with open(MONTHLY_DATA_FILE) as f:
        monthly_data = json.load(f)
else:
    monthly_data = {}

# --- Fetch clan info ---
encoded_tag = CLAN_TAG.replace("#", "%23")
headers_api = {"Authorization": f"Bearer {API_KEY}", "Accept": 
"application/json"}

try:
    response = requests.get(f"https://api.clashofclans.com/v1/clans/{encoded_tag}", 
headers=headers_api)
    response.raise_for_status()
    clan = response.json()
except requests.exceptions.RequestException as e:
    print("Error fetching clan info:", e)
    exit()

# --- Fetch live clan members for donations ---
try:
    members_resp = requests.get(f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members", 
headers=headers_api)
    members_resp.raise_for_status()
    clan_members = members_resp.json().get("items", [])
except requests.exceptions.RequestException as e:
    print("Error fetching clan members:", e)
    clan_members = []

# --- Prepare separate leaderboards ---
war_stars_list = []
donations_list = []

for member in clan_members:
    tag = member.get("tag")
    name = member.get("name", "Unknown")
    donations = member.get("donations", 0)
    donations_received = member.get("donationsReceived", 0)
    war_stars = monthly_data.get(tag, {}).get("stars", 0)
    # Build separate lists
    war_stars_list.append((name, war_stars))
    donations_list.append((name, donations))

# Sort descending
war_stars_list.sort(key=lambda x: x[1], reverse=True)
donations_list.sort(key=lambda x: x[1], reverse=True)

# Format leaderboard text
war_stars_text = "\n".join([f"{i+1}. {name}: {stars}" for i, (name, 
stars) in enumerate(war_stars_list)]) or "No war stars yet."
donations_text = "\n".join([f"{i+1}. {name}: {donations}" for i, (name, 
donations) in enumerate(donations_list)]) or "No donations yet."

# --- Determine Gold Pass winners ---
top_war_stars = war_stars_list[0][0] if war_stars_list else "N/A"
top_donations = donations_list[0][0] if donations_list else "N/A"

# Save winners in monthly_data
monthly_data['gold_pass_war_stars'] = top_war_stars
monthly_data['gold_pass_donations'] = top_donations
with open(MONTHLY_DATA_FILE, "w") as f:
    json.dump(monthly_data, f, indent=2)

# --- Clan war stats ---
war_wins = clan.get("warWins", 0)
war_losses = clan.get("warLosses", 0)
war_draws = clan.get("warTies", 0)
total_wars = war_wins + war_losses + war_draws
war_win_pct = f"{(war_wins / total_wars * 100):.1f}%" if total_wars > 0 else "N/A"

# --- Build embed ---
embed = {
    "title": f"{clan.get('name', 'AMA')} | Clan Overview",
    "description": (
        f"Clan Tag: {clan.get('tag', CLAN_TAG)}\n"
        f"Clan Level: {clan.get('clanLevel', 'N/A')}\n"
        f"Members: {clan.get('members', 0)}/{clan.get('memberLimit', 50)}\n"
        f"War Wins/Losses/Draws: {war_wins}/{war_losses}/{war_draws}\n"
        f"War Win Streak: {clan.get('warWinStreak','N/A')}\n"
        f"War Win %: {war_win_pct}"
    ),
    "color": 3447003,
    "thumbnail": {"url": CLAN_LOGO_URL},
    "fields": [
        {"name": "Monthly Leaderboard: War Stars", "value": 
war_stars_text, "inline": False},
        {"name": "Monthly Leaderboard: Donations", "value": 
donations_text, "inline": False},
        {"name": "Gold Pass Winners", "value": f"🏆 War Stars: {top_war_stars}\n🏆 Donations: {top_donations}", "inline": False}
    ],
    "footer": {"text": "Updated automatically via Clash API"}
}

payload = {"embeds": [embed]}

# --- Send/update embed via bot ---
base_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
headers_bot = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": 
"application/json"}
message_id = get_saved_message_id()

def post_new_message():
    r = requests.post(base_url, headers=headers_bot, json=payload)
    if r.status_code == 200:
        save_message_id(r.json()["id"])
        print("Clan overview embed posted successfully!")
    else:
        print("Error posting embed:", r.status_code, r.text)

if message_id:
    patch_url = f"{base_url}/{message_id}"
    r = requests.patch(patch_url, headers=headers_bot, json=payload)
    if r.status_code == 200:
        print("Clan overview embed updated!")
    else:
        print("Saved message missing or invalid, posting new embed...")
        post_new_message()
else:
    post_new_message()
