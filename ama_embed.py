import requests
import os

# ----------- CONFIG -----------
CLAN_TAG = "#2CYV200G"  # Your clan tag
API_KEY = os.getenv("COC_API_KEY")
WEBHOOK_URL = "https://discord.com/api/webhooks/1477650976381862029/LwdpoEXxRlEu_64WDBmswebMAselXIe1Qrqk6UvkxDmVYZGrBG41vqv7lARhysaWk6t7"
CLAN_LOGO_URL = "https://i.ibb.co/5Wj8xQPN/9-F22-C364-28-C1-4-B5-C-BADF-6-FC08294-FD45.jpg"
# ------------------------------

encoded_tag = CLAN_TAG.replace("#", "%23")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

# Fetch clan data from Clash API
response = requests.get(
    f"https://api.clashofclans.com/v1/clans/{encoded_tag}",
    headers=headers
)

if response.status_code != 200:
    print("Error fetching clan info:")
    print(response.status_code, response.text)
    exit()

clan = response.json()

# Build Discord embed
embed = {
    "username": "AMA Recruitment",
    "avatar_url": CLAN_LOGO_URL,
    "embeds": [
        {
            "title": f"{clan['name']} | Relaxed Farming Clan",
            "description": "Relaxed farming clan that locks in for War & CWL. TH9+ welcome. No donation requirements.",
            "color": 3447003,
            "thumbnail": {"url": CLAN_LOGO_URL},
            "fields": [
                {"name": "Clan Tag", "value": clan['tag'], "inline": True},
                {"name": "Members", "value": f"{clan['members']} / 50", "inline": True},
                {"name": "Clan Level", "value": str(clan['clanLevel']), "inline": True},
                {"name": "Required Trophies", "value": str(clan['requiredTrophies']), "inline": True},
                {"name": "War Stars", "value": str(clan.get('warStars', 'N/A')), "inline": True}
            ],
            "footer": {
                "text": "705W - 162L | Stay active, be friendly, and join us for organized wars! 💪"
            }
        }
    ]
}

# Send embed to Discord
discord_response = requests.post(WEBHOOK_URL, json=embed)

if discord_response.status_code == 204:
    print("Embed posted successfully!")
else:
    print("Failed to post embed:")
    print(discord_response.status_code, discord_response.text)
