from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def require_int_env(name: str) -> int:
    value = require_env(name)
    try:
        return int(value)
    except ValueError:
        raise RuntimeError(
            f"Environment variable {name} must be an integer, got: {value}"
        )


DISCORD_TOKEN = require_env("DISCORD_BOT_TOKEN")
CLASH_API_KEY = require_env("CLASH_API_KEY")

CLAN_TAGS = [
    tag for tag in [
        os.getenv("CLAN_TAG"),
        os.getenv("FEEDER_CLAN_TAG"),
    ]
    if tag
]
MAIN_CLAN_TAG = CLAN_TAGS[0] if CLAN_TAGS else None

WAR_CHANNEL_ID = require_int_env("WAR_CHANNEL_ID")
FEEDER_WAR_CHANNEL_ID = int(os.getenv("FEEDER_WAR_CHANNEL_ID", "0") or 0)
CLAN_STATS_CHANNEL_ID = require_int_env("LEADERBOARD_CHANNEL_ID")
WAR_SUMMARY_CHANNEL_ID = require_int_env("WAR_SUMMARY_CHANNEL_ID")
LEADER_ROLE_ID = require_int_env("LEADER_ROLE_ID")
CO_LEADER_ROLE_ID = require_int_env("CO_LEADER_ROLE_ID")
CLAN_CHAT_CHANNEL_ID = require_int_env("CLAN_CHAT_CHANNEL_ID")
WAR_MVP_ROLE_ID = int(os.getenv("WAR_MVP_ROLE_ID", "0") or 0)

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
ASSETS_DIR = os.getenv("ASSETS_DIR", "/app/assets")
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "/app/clan_bot/templates")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

UNLINKED_WARN_FILE = os.path.join(DATA_DIR, "unlinked_warned.json")
WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
DONATION_FILE = os.path.join(DATA_DIR, "donations.json")
LINKED_FILE = os.path.join(DATA_DIR, "linked_players.json")
WAR_PINGS_FILE = os.path.join(DATA_DIR, "war_pings.json")
WAR_END_FILE = os.path.join(DATA_DIR, "war_end.json")
WAR_SUMMARY_POSTS_FILE = os.path.join(DATA_DIR, "war_summary_posts.json")
PERFORMANCE_FILE = os.path.join(DATA_DIR, "player_performance.json")
WAR_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "war_template.html")
FINAL_WAR_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "final_war_template.html")
FINAL_WAR_IMAGE_PATH = "/app/final_war.png"
DONATION_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "donation_template.html")
DONATION_IMAGE_PATH = "/app/donations.png"
GOLD_LEADERBOARD_IMAGE_PATH = "/app/gold_leaderboard.png"
MONTHLY_MVP_FILE = os.path.join(DATA_DIR, "monthly_mvp.json")
CURRENT_WAR_MVP_FILE = os.path.join(DATA_DIR, "current_war_mvp.json")
COINS_FILE = os.path.join(DATA_DIR, "coins.json")
SHOP_FILE = os.path.join(DATA_DIR, "shop.json")
CACHE_FILE = os.path.join(DATA_DIR, "api_cache.json")
LOOT_DROP_FILE = os.path.join(DATA_DIR, "loot_drop.json")

LOOT_DROP_MIN_MINUTES = 45
LOOT_DROP_MAX_MINUTES = 90

HEADERS = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}
