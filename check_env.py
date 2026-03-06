# check_env.py
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Read variables
API_KEY = os.getenv("COC_API_KEY")
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")

# Print results (only print the last 4 chars of keys for safety)
print("CLAN_TAG:", CLAN_TAG)
print("API_KEY loaded:", "Yes" if API_KEY else "No")
if API_KEY:
    print("API_KEY (last 4 chars):", API_KEY[-4:])
print("BOT_TOKEN loaded:", "Yes" if BOT_TOKEN else "No")
if BOT_TOKEN:
    print("BOT_TOKEN (last 4 chars):", BOT_TOKEN[-4:])
