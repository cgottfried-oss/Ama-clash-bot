# ---------------- ENVIRONMENT ----------------

import os
import io
import json
import html as html_lib
import aiohttp
import asyncio
import signal
import re
import traceback
import random
import time
from html_renderer import render_html_to_png_buffer, close_playwright_renderer
from renderers.war_renderer import render_war_template_to_png, render_final_war_template_to_png
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from upgrade_advisor import register_upgrade_advisor
from commands import register_all_commands
from storage import safe_load_json, safe_save_json, update_json_file
from linked_accounts import normalize_tag, normalize_user_linked_data as normalize_linked_data, build_tag_to_discord_map
from reward_config import (
    STAR_COIN_REWARD, WAR_MVP_BONUS, CLUTCH_COIN_REWARD, CLUTCH_REWARD_TIERS,
    ADVISOR_DAILY_SYNC_REWARD, ADVISOR_PROGRESS_REWARDS, ADVISOR_GROUP_REWARDS,
)
from shop_config import SHOP_ITEMS, LOOT_DROP_STYLES
from mvp_roles import (
    generate_war_mvp_title,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
)
from runtime import (
    create_clash_client,
    create_economy_manager,
    create_war_runtime_context,
)
import discord
from tasks.update_loop import run_update_cycle
from features.donations import update_donation_leaderboard as donation_update
from features.clutch_posts import post_clutch_moment, post_clutch_summary
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv
from clan_snapshot.commands import register_clan_snapshot_command
from war import clutch as war_clutch
from war import mvp as war_mvp
from war import summaries as war_summaries
from war import planning as war_planning
from war import images as war_images
from war import rewards as war_rewards
from progress.commands import register_current_progress_command
import loot_drops

# Load .env
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

# ---------------- PATHS ----------------

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
ASSETS_DIR = "/app/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)
TEMPLATES_DIR = "/app/templates"

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
COIN_LEADERBOARD_IMAGE_PATH = "/app/coin_leaderboard.png"
MONTHLY_MVP_FILE = os.path.join(DATA_DIR, "monthly_mvp.json")
CURRENT_WAR_MVP_FILE = os.path.join(DATA_DIR, "current_war_mvp.json")
COINS_FILE = os.path.join(DATA_DIR, "coins.json")
SHOP_FILE = os.path.join(DATA_DIR, "shop.json")
LOOT_DROP_MIN_MINUTES = 45
LOOT_DROP_MAX_MINUTES = 90
LOOT_DROP_FILE = os.path.join(DATA_DIR, "loot_drop.json")

# Track already announced clutch attacks (prevents spam)

def get_clutch_scope_key(war):

    return war_clutch.get_clutch_scope_key(war, normalize_tag)

def get_clutch_log_file(war):

    return war_clutch.get_clutch_log_file(

        war,

        data_dir=DATA_DIR,

        normalize_tag=normalize_tag,

    )

def get_clutch_state_file(war):

    return war_clutch.get_clutch_state_file(

        war,

        data_dir=DATA_DIR,

        normalize_tag=normalize_tag,
    )

TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$")
HEADERS = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}


def clan_scope_key(clan_tag: str | None) -> str:
    """Stable short key for per-clan message/state files."""
    normalized = normalize_tag(clan_tag or "")
    return (normalized or "main").replace("#", "")


def is_main_clan_tag(clan_tag: str | None) -> bool:
    return bool(MAIN_CLAN_TAG and normalize_tag(clan_tag or "") == normalize_tag(MAIN_CLAN_TAG))


def scoped_state_file(base_path: str, clan_tag: str | None) -> str:
    """
    Keep the original AMA filenames for the main clan so existing message IDs/state survive,
    and use suffixed files for the feeder so wars never overwrite each other.
    """
    if is_main_clan_tag(clan_tag):
        return base_path
    root, ext = os.path.splitext(base_path)
    return f"{root}_{clan_scope_key(clan_tag)}{ext or '.txt'}"


def war_channel_id_for_clan(clan_tag: str | None) -> int:
    """
    AMA uses WAR_CHANNEL_ID. Feeder uses FEEDER_WAR_CHANNEL_ID when configured;
    otherwise it falls back to the same current-war channel.
    """
    if is_main_clan_tag(clan_tag):
        return WAR_CHANNEL_ID
    return FEEDER_WAR_CHANNEL_ID or WAR_CHANNEL_ID


async def reset_war_pings(clan_tag: str | None = None):
    await safe_save_json(scoped_state_file(WAR_PINGS_FILE, clan_tag), {})

# ---------------- CONSTANTS ----------------

# SHOP_ITEMS and LOOT_DROP_STYLES live in shop_config.py.
# Keep economy/reward tuning in reward_config.py.

# ---------------- DISCORD ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
class ClanBot(commands.Bot):
    async def close(self):
        print("Shutting down bot and closing HTTP session...")
        await close_session()
        await close_playwright_renderer()
        await super().close()

bot = ClanBot(command_prefix="/", intents=intents)
tree = bot.tree

# ---------------- GLOBALS/COOLDOWNS ----------------

session: aiohttp.ClientSession | None = None
api_cache = {}
file_lock = asyncio.Lock()
loot_drop_lock = asyncio.Lock()

economy = create_economy_manager()

# ---------------- HELPER FUNCTIONS ----------------

def get_opponent_member(war, member_tag):
    member_tag = normalize_tag(member_tag or "")
    if not member_tag:
        return None

    for member in war.get("opponent", {}).get("members", []):
        if normalize_tag(member.get("tag", "")) == member_tag:
            return member

    return None


def get_clan_member(war, member_tag):
    member_tag = normalize_tag(member_tag or "")
    if not member_tag:
        return None

    for member in war.get("clan", {}).get("members", []):
        if normalize_tag(member.get("tag", "")) == member_tag:
            return member

    return None


def get_defender_position(attack, war):
    defender = get_opponent_member(war, attack.get("defenderTag", ""))
    if not defender:
        return None
    return defender.get("mapPosition")


def get_attacker_position(attack, war, attacker_tag=None):
    attacker = get_clan_member(war, attacker_tag or attack.get("attackerTag", ""))
    if not attacker:
        return None
    return attacker.get("mapPosition")


def get_defender_townhall_level(attack, war):
    defender = get_opponent_member(war, attack.get("defenderTag", ""))
    if not defender:
        return None
    return defender.get("townhallLevel") or defender.get("townHallLevel")


def get_attacker_townhall_level(attack, war, attacker_tag=None):
    attacker = get_clan_member(war, attacker_tag or attack.get("attackerTag", ""))
    if not attacker:
        return None
    return attacker.get("townhallLevel") or attacker.get("townHallLevel")


def get_war_signature(war):
    clan_tag = normalize_tag(war.get("clan", {}).get("tag", ""))
    opponent_tag = normalize_tag(war.get("opponent", {}).get("tag", ""))
    start_time = war.get("startTime", "")
    end_time = war.get("endTime", "")
    return f"{clan_tag}_{opponent_tag}_{start_time}_{end_time}"


def build_attack_id(member_tag, attack):

    return war_clutch.build_attack_id(member_tag, attack, normalize_tag)


def collect_clan_attacks(war):

    return war_clutch.collect_clan_attacks(war, normalize_tag)


def get_prior_best_on_defender(war, defender_tag, attack_order):

    return war_clutch.get_prior_best_on_defender(

        war,

        defender_tag,

        attack_order,

        normalize_tag,

    )


def classify_war_state(star_diff, destruction_diff):

    return war_clutch.classify_war_state(star_diff, destruction_diff)


def get_attack_impact(attack, war):

    return war_clutch.get_attack_impact(attack, war, normalize_tag)


def is_clutch_attack(attack, war, attacker_tag=None):

    return war_clutch.is_clutch_attack(

        attack,

        war,

        attacker_tag=attacker_tag,

        get_defender_position=get_defender_position,

        get_attacker_position=get_attacker_position,

        get_attacker_townhall_level=get_attacker_townhall_level,

        get_defender_townhall_level=get_defender_townhall_level,

        normalize_tag=normalize_tag,

    )

async def process_clutch_attacks(war):
    clan = war.get("clan") or {}
    clan_tag = normalize_tag(clan.get("tag", ""))
    if not clan_tag:
        print(f"[CLUTCH] Skipping clutch processing: missing clan tag. War keys: {list(war.keys())}")
        return

    log_file = get_clutch_log_file(war)
    state_file = get_clutch_state_file(war)
    if not log_file or not state_file:
        print(f"[CLUTCH] Skipping clutch processing: unable to build clutch files for clan tag '{clan_tag}'")
        return

    print(f"[CLUTCH] Processing clan tag: {clan_tag}")

    log = await safe_load_json(log_file)
    if not isinstance(log, list):
        log = []

    state = await safe_load_json(state_file)
    if not isinstance(state, dict):
        state = {}

    war_signature = get_war_signature(war)
    stored_signature = state.get("war_signature")
    initialized = state.get("initialized", False)
    new_log = set(log)

    current_attack_ids = set()
    new_clutch_hits = []

    for side in ["clan"]:
        members = war.get(side, {}).get("members", [])

        for member in members:
            member_tag = member.get("tag", "")
            member_name = member.get("name", "Someone")
            attacks = member.get("attacks", [])

            for attack in attacks:
                attack_id = build_attack_id(member_tag, attack)
                current_attack_ids.add(attack_id)

                if attack_id in new_log:
                    continue

                clutch_type = is_clutch_attack(attack, war, attacker_tag=member_tag)
                if not clutch_type:
                    continue

                new_clutch_hits.append(
                    {
                        "attack": attack,
                        "attacker_tag": member_tag,
                        "attacker_name": member_name,
                        "attack_id": attack_id,
                        "clutch_type": clutch_type,
                    }
                )

    if stored_signature != war_signature:
        await safe_save_json(log_file, list(current_attack_ids))
        await safe_save_json(
            state_file,
            {"war_signature": war_signature, "initialized": True},
        )
        return

    if not initialized:
        seeded_log = new_log | current_attack_ids
        await safe_save_json(log_file, list(seeded_log))
        await safe_save_json(
            state_file,
            {"war_signature": war_signature, "initialized": True},
        )
        return

    if not new_clutch_hits:
        await safe_save_json(log_file, list(new_log | current_attack_ids))
        return

    if len(new_clutch_hits) > 2:
        await post_clutch_summary(
            channel=bot.get_channel(CLAN_CHAT_CHANNEL_ID),
            war=war,
            clutch_hits=new_clutch_hits,
            get_defender_position=get_defender_position,
            get_clutch_reward_amount=get_clutch_reward_amount,
        )
        for hit in new_clutch_hits:
            await reward_clutch_coins(hit["attacker_tag"], hit["attacker_name"], hit["attack_id"], clutch_type=hit["clutch_type"])
            new_log.add(hit["attack_id"])
    else:
        for hit in new_clutch_hits:
            await post_clutch_moment(
                channel=bot.get_channel(CLAN_CHAT_CHANNEL_ID),
                attack=hit["attack"],
                war=war,
                attacker_tag=hit["attacker_tag"],
                attacker_name=hit["attacker_name"],
                attack_id=hit["attack_id"],
                clutch_type=hit["clutch_type"],
                get_defender_position=get_defender_position,
                resolve_discord_mention=resolve_discord_mention,
                reward_clutch_coins=reward_clutch_coins,
                normalize_tag=normalize_tag,
            )
            new_log.add(hit["attack_id"])

    await safe_save_json(log_file, list(new_log | current_attack_ids))
    await safe_save_json(
        state_file,
        {"war_signature": war_signature, "initialized": True},
    )
# ---------------- CACHE SYSTEM ----------------

clash_api_client = create_clash_client(
    safe_load_json=safe_load_json,
    safe_save_json=safe_save_json,
)

async def load_cache():

    return await clash_api_client.load_cache()

async def save_cache(cache):

    clash_api_client.api_cache = cache if isinstance(cache, dict) else {}

    await clash_api_client.save_cache()

async def get_cached_or_fetch(key, url, ttl=120):

    return await clash_api_client.get_cached_or_fetch(key, url, ttl=ttl)

war_runtime = create_war_runtime_context(
    bot=bot,
    economy=economy,
    safe_load_json=safe_load_json,
    safe_save_json=safe_save_json,
    update_json_file=update_json_file,
    normalize_tag=normalize_tag,
    normalize_linked_data=normalize_linked_data,
    build_tag_to_discord_map=build_tag_to_discord_map,
    get_cached_or_fetch=get_cached_or_fetch,
)
    
# ---------------- UPGRADE ADVISOR ----------------

upgrade_advisor = register_upgrade_advisor(
    tree,
    {
        "safe_load_json": safe_load_json,
        "safe_save_json": safe_save_json,
        "update_json_file": update_json_file,
        "normalize_tag": normalize_tag,
        "get_cached_or_fetch": get_cached_or_fetch,
        "linked_file": LINKED_FILE,
        "data_dir": DATA_DIR,
        "clash_api_base": "https://api.clashofclans.com/v1",
    },
)

register_current_progress_command(
    tree,
    get_cached_or_fetch=get_cached_or_fetch,
    normalize_tag=normalize_tag,
    safe_load_json=safe_load_json,
    linked_file=LINKED_FILE,
    assets_dir=ASSETS_DIR,
    clash_api_base="https://api.clashofclans.com/v1",
)

register_clan_snapshot_command(
    tree,
    get_cached_or_fetch=get_cached_or_fetch,
    normalize_tag=normalize_tag,
    clan_tags=CLAN_TAGS,
    clash_api_base="https://api.clashofclans.com/v1",
)

async def load_performance():
    return await safe_load_json(PERFORMANCE_FILE)
    
def get_season_key():
    return datetime.now(timezone.utc).strftime("%Y-%m")

def get_war_id(war):
    return war_rewards.get_war_id(war)


def get_war_result(clan: dict, opponent: dict):
    return war_rewards.get_war_result(clan, opponent)


def get_war_banner_stat_multiplier(member, tag_to_discord=None, shop_data=None, now=None):
    return war_rewards.get_war_banner_stat_multiplier(
        member,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
    )


def get_war_member_performance(member, tag_to_discord=None, shop_data=None, now=None):
    return war_rewards.get_war_member_performance(
        member,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
    )


def get_war_mvp_stats(war, tag_to_discord=None, shop_data=None, now=None):
    return war_rewards.get_war_mvp_stats(
        war,
        tag_to_discord,
        shop_data,
        now,
        economy=economy,
    )


async def update_monthly_mvp_from_war(war):
    return await war_rewards.update_monthly_mvp_from_war(
        war,
        economy=economy,
        linked_file=LINKED_FILE,
        monthly_mvp_file=MONTHLY_MVP_FILE,
        safe_load_json=safe_load_json,
        update_json_file=update_json_file,
    )


async def post_war_mvp_announcement(war, channel: discord.abc.Messageable | None = None, war_rewards=None):
    return await war_rewards.post_war_mvp_announcement(
        war,
        channel=channel,
        war_rewards=war_rewards,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
        bot=bot,
        economy=economy,
        linked_file=LINKED_FILE,
        current_war_mvp_file=CURRENT_WAR_MVP_FILE,
        war_mvp_role_id=WAR_MVP_ROLE_ID,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        reward_war_coins=reward_war_coins,
        format_member_mention=format_member_mention,
    )


def get_current_monthly_mvp(stored_donations):
    players = (stored_donations or {}).get("players", {})
    if not isinstance(players, dict) or not players:
        return None, None

    best_tag, best_data = max(
        players.items(),
        key=lambda item: (
            item[1].get("donations", 0),
            -item[1].get("received", 0),
            item[1].get("name", "")
        )
    )
    return best_data.get("name") or best_tag, best_data
    
def choose_weighted_loot_style():
    total_weight = sum(style["weight"] for style in LOOT_DROP_STYLES)
    roll = random.uniform(0, total_weight)
    current = 0

    for style in LOOT_DROP_STYLES:
        current += style["weight"]
        if roll <= current:
            return style

    return LOOT_DROP_STYLES[0]

def choose_weighted_loot_style():
    return loot_drops.choose_weighted_loot_style(
        loot_drop_styles=LOOT_DROP_STYLES,
    )


async def load_loot_drop():
    return await loot_drops.load_loot_drop(
        safe_load_json=safe_load_json,
        loot_drop_file=LOOT_DROP_FILE,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
    )


async def schedule_next_loot_drop():
    return await loot_drops.schedule_next_loot_drop(
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        loot_drop_file=LOOT_DROP_FILE,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
        loot_drop_min_minutes=LOOT_DROP_MIN_MINUTES,
        loot_drop_max_minutes=LOOT_DROP_MAX_MINUTES,
    )


async def create_loot_drop():
    return await loot_drops.create_loot_drop(
        bot=bot,
        economy=economy,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        loot_drop_file=LOOT_DROP_FILE,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
        loot_drop_styles=LOOT_DROP_STYLES,
        loot_drop_lock=loot_drop_lock,
    )


async def claim_loot_drop(message: discord.Message):
    return await loot_drops.claim_loot_drop(
        message,
        economy=economy,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        normalize_linked_data=normalize_linked_data,
        linked_file=LINKED_FILE,
        loot_drop_file=LOOT_DROP_FILE,
        clan_chat_channel_id=CLAN_CHAT_CHANNEL_ID,
        loot_drop_styles=LOOT_DROP_STYLES,
        loot_drop_lock=loot_drop_lock,
        shop_items=SHOP_ITEMS,
        schedule_next_loot_drop_func=schedule_next_loot_drop,
    )
    
async def load_coins():
    return await economy.load_coins()

async def load_shop_data():
    return await economy.load_shop_data()

async def get_user_shop_entry(user_id: str):
    return await economy.get_user_shop_entry(user_id)

async def add_shop_item(user_id: str, item_key: str, amount: int = 1):
    await economy.add_shop_item(user_id, item_key, amount)

async def consume_shop_item(user_id: str, item_key: str):
    return await economy.consume_shop_item(user_id, item_key)

async def equip_shop_item(user_id: str, item_key: str, slot: str):
    return await economy.equip_shop_item(user_id, item_key, slot)

async def activate_shop_effect(user_id: str, item_key: str, duration_seconds: int):
    return await economy.activate_shop_effect(user_id, item_key, duration_seconds)

async def get_active_shop_effects(user_id: str):
    return await economy.get_active_shop_effects(user_id)

async def steal_coins(**kwargs):
    return await economy.steal_coins(**kwargs)

async def spend_coins(user_id: str, amount: int):
    return await economy.spend_coins(user_id, amount)

async def get_inventory_text(user_id: str):
    return await economy.get_inventory_text(user_id)

def format_member_mention(discord_id, fallback_name: str) -> str:
    if discord_id:
        return f"<@{discord_id}>"
    return fallback_name or "Unknown"

async def resolve_discord_mention(member_tag: str | None, fallback_name: str = "Unknown") -> str:
    normalized_member_tag = normalize_tag(member_tag or "")
    if not normalized_member_tag:
        return fallback_name or "Unknown"

    try:
        linked_raw = await safe_load_json(LINKED_FILE)
        linked = normalize_linked_data(linked_raw)
        tag_to_discord = build_tag_to_discord_map(linked)
        discord_id = tag_to_discord.get(normalized_member_tag)
        return format_member_mention(discord_id, fallback_name)
    except Exception as e:
        print(f"[MENTION RESOLVE ERROR] tag={normalized_member_tag}: {e}")
        return fallback_name or "Unknown"

def get_war_mvp_member(war, tag_to_discord=None, shop_data=None, now=None):

    return war_mvp.get_war_mvp_member(

        war,

        tag_to_discord,

        shop_data,

        now,

        economy=economy,

        shop_items=SHOP_ITEMS,

    )

async def reward_war_coins(war):
    tag_to_discord, shop_data, banner_now = await load_war_banner_context()

    def boosted_mvp_member(war_payload):
        return get_war_mvp_member(war_payload, tag_to_discord, shop_data, banner_now)

    return await economy.reward_war_coins(war, get_war_id=get_war_id, get_war_mvp_member=boosted_mvp_member)

async def reward_clutch_coins(member_tag, member_name, attack_id, clutch_type=None):
    return await economy.reward_clutch_coins(member_tag, member_name, attack_id, clutch_type=clutch_type)

def get_clutch_reward_amount(clutch_type):
    return war_clutch.get_clutch_reward_amount(
        clutch_type,
        CLUTCH_REWARD_TIERS,
        CLUTCH_COIN_REWARD,
    )

async def post_final_war_summary(war, war_rewards=None):
    return await war_summaries.post_final_war_summary(
        war=war,
        war_rewards=war_rewards,
        bot=bot,
        war_summary_channel_id=WAR_SUMMARY_CHANNEL_ID,
        war_summary_posts_file=WAR_SUMMARY_POSTS_FILE,
        current_war_mvp_file=CURRENT_WAR_MVP_FILE,
        war_mvp_role_id=WAR_MVP_ROLE_ID,
        get_war_id=get_war_id,
        clan_scope_key=clan_scope_key,
        get_war_result=get_war_result,
        create_final_war_image=create_final_war_image,
        load_war_banner_context=load_war_banner_context,
        get_war_mvp_stats=get_war_mvp_stats,
        format_member_mention=format_member_mention,
        rotate_war_mvp_role=rotate_war_mvp_role,
        update_war_mvp_role_presentation=update_war_mvp_role_presentation,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
    )

# ---------------- HTTP SESSION MANAGEMENT ----------------

async def get_session():

    return await clash_api_client.get_session()

async def close_session():

    await clash_api_client.close()

# ---------------- Clash API ----------------

async def fetch_json(url, retries=3):

    return await clash_api_client.fetch_json(url, retries=retries)

async def fetch_clan_data(clan_tag: str):

    return await clash_api_client.fetch_clan_data(clan_tag)


async def fetch_all_data():
    if not MAIN_CLAN_TAG:
        print("⚠️ No main clan tag configured")
        return None, None

    return await fetch_clan_data(MAIN_CLAN_TAG)

# ---------------- WAR PLAN ----------------

def build_war_plan_data(war, data):
    return war_planning.build_war_plan_data(war, data)


def render_war_plan_html(plan_data):
    return war_planning.render_war_plan_html(plan_data)


def inject_large_war_plan_css(html: str, target_count: int) -> str:
    return war_planning.inject_large_war_plan_css(html, target_count)

# ---------------- BATTLE DAY UI ----------------

async def create_war_image(war, ai_data):
    return await war_images.create_war_image(
        war=war,
        ai_data=ai_data,
        war_template_path=WAR_TEMPLATE_PATH,
        load_war_banner_context=load_war_banner_context,
        get_war_member_performance=get_war_member_performance,
        build_war_plan_data=build_war_plan_data,
        render_war_plan_html=render_war_plan_html,
        inject_large_war_plan_css=inject_large_war_plan_css,
        render_html_to_png_buffer=render_html_to_png_buffer,
    )

# ---------------- WAR SUMMARY IMAGE ----------------

async def create_final_war_image(war):
    return await war_images.create_final_war_image(
        war=war,
        final_war_template_path=FINAL_WAR_TEMPLATE_PATH,
        load_war_banner_context=load_war_banner_context,
        get_war_member_performance=get_war_member_performance,
        get_war_result=get_war_result,
        get_war_mvp_stats=get_war_mvp_stats,
        render_html_to_png_buffer=render_html_to_png_buffer,
    )

# ---------------- WAR BANNER ----------------

async def load_war_banner_context():
    return await war_rewards.load_war_banner_context(
        safe_load_json=safe_load_json,
        linked_file=LINKED_FILE,
        economy=economy,
    )

# ---------------- DONATION LEADERBOARD ----------------

# Donation leaderboard rendering/posting is handled by features/donations.py.

# ---------------- AI WAR PLAN ----------------

async def generate_attack_suggestions(war):
    from datetime import datetime, timezone

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    clan_members = clan.get("members", [])
    opponent_members = opponent.get("members", [])

    def already_tripled(target):
        best = target.get("bestOpponentAttack")
        return bool(best and best.get("stars") == 3)

    # Remove already tripled bases
    opponent_members = [t for t in opponent_members if not already_tripled(t)]

    performance = await load_performance()
    tag_to_discord, shop_data, banner_now = await load_war_banner_context()

    suggestions = []
    assignments = []
    player_usage = {}
    MAX_HITS = 2
    real_usage = {m.get("name"): len(m.get("attacks", [])) for m in clan_members}

# ---------------- WAR PHASE ----------------

    end_time = war.get("endTime")
    hours_left = 24

    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(
            tzinfo=timezone.utc
        )
        remaining = end_dt - datetime.now(timezone.utc)
        hours_left = remaining.total_seconds() / 3600

    if hours_left > 12:
        phase = "early"
    elif hours_left > 3:
        phase = "mid"
    else:
        phase = "late"

# ---------------- STRATEGY ----------------

    clan_stars = clan.get("stars", 0)
    opp_stars = opponent.get("stars", 0)
    star_diff = clan_stars - opp_stars
    
# ---------------- FORCED WIN / PERFECT WAR DETECTION ----------------

    team_size = war.get("teamSize", 0) or 0
    attacks_per_member = war.get("attacksPerMember", 2) or 2
    max_attacks = team_size * attacks_per_member
    max_possible_stars = team_size * 3
    
    clan_attacks_used = clan.get("attacks", 0) or 0
    opp_attacks_used = opponent.get("attacks", 0) or 0
    
    remaining_enemy_attacks = max_attacks - opp_attacks_used
    enemy_max_possible_stars = opp_stars + (remaining_enemy_attacks * 3)
    
    # PERFECT WAR
    if clan_stars >= max_possible_stars:
        return {
            "phase": "victory",
            "strategy": "perfect war",
            "win_chance": 100.0,
            "mvp": (
                max(
                    [m for m in clan.get("members", []) if m.get("attacks")],
                    key=lambda m: len(m.get("attacks", [])) * 10
                    + sum(a.get("stars", 0) for a in m.get("attacks", [])),
                    default={}
                ).get("name", "TBD")
            ),
            "targets": []
        }
    
    # MATHEMATICALLY SECURED WIN
    if clan_stars > enemy_max_possible_stars:
        return {
            "phase": "victory",
            "strategy": "secured",
            "win_chance": 100.0,
            "mvp": (
                max(
                    [m for m in clan.get("members", []) if m.get("attacks")],
                    key=lambda m: len(m.get("attacks", [])) * 10
                    + sum(a.get("stars", 0) for a in m.get("attacks", [])),
                    default={}
                ).get("name", "TBD")
            ),
            "targets": []
        }

    if phase == "late":
        if star_diff < 0:
            strategy = "comeback"
        elif star_diff > 5:
            strategy = "secure"
        else:
            strategy = "balanced"
    else:
        strategy = "standard"

# ---------------- PLAYER PERFORMANCE ----------------

    def player_score(m):
        name = m.get("name")
        attacks = m.get("attacks", [])
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        th = m.get("townhallLevel") or 0

        base = stars * 100 + destruction + (th * 25)
        base *= get_war_banner_stat_multiplier(m, tag_to_discord, shop_data, banner_now)

        if name in performance:
            data = performance[name]
            if data.get("attacks", 0) > 0:
                triple_rate = data.get("triples", 0) / data["attacks"]
                fail_rate = data.get("fails", 0) / data["attacks"]

                base += triple_rate * 200
                base -= fail_rate * 150
                base += data.get("vs_equal", 0) * 8
                base += data.get("vs_higher", 0) * 12

        return base

    def is_rushed(player):
        th = player.get("townhallLevel") or 0
        name = player.get("name")
        data = performance.get(name, {})

        attacks = data.get("attacks", 0)
        triple_rate = (data.get("triples", 0) / attacks) if attacks > 0 else 0

        return th >= 13 and triple_rate < 0.35

# ---------------- HELPERS ----------------

    def can_use_player(name):
        return real_usage.get(name, 0) + player_usage.get(name, 0) < MAX_HITS

    def already_hit_target(player, target):
        for attack in player.get("attacks", []):
            if attack.get("defenderTag") == target.get("tag"):
                return True
        return False

    def allowed_th_gap(target_th):
        if target_th >= 17:
            return 1
        elif target_th >= 15:
            return 2
        return 2 if phase == "early" else 3

    def is_eligible(player, target, allow_desperation=False):
        player_th = player.get("townhallLevel") or 0
        target_th = target.get("townhallLevel") or 0

        gap = target_th - player_th
        max_gap = allowed_th_gap(target_th)

        if player_th >= 15 and target_th <= 12:
            return False

        if is_rushed(player) and target_th > player_th:
            return False

        if allow_desperation and phase == "late" and strategy == "comeback":
            max_gap += 1

        return gap <= max_gap

    def attacker_score(player, target):
        player_th = player.get("townhallLevel") or 0
        target_th = target.get("townhallLevel") or 0
        th_gap = target_th - player_th

        base = player_score(player)

        if is_rushed(player) and th_gap > 0:
            base -= 250

        if player_th >= 15 and th_gap <= -2:
            base -= 350

        if th_gap == 0:
            base += 120
        elif th_gap == -1:
            base += 20
        elif th_gap <= -2:
            base -= 250
        elif th_gap == 1:
            base -= 100
        elif th_gap == 2:
            base -= 220
        else:  # th_gap > 2
            base -= 400

        used = real_usage.get(player.get("name"), 0) + player_usage.get(
            player.get("name"), 0
        )
        if used == 0:
            base += 25

        return base

    def target_priority(target):
        """
        Higher score = more deserving of an assignment earlier.
        """
        th = target.get("townhallLevel") or 0
        pos = target.get("mapPosition") or 99
        best = target.get("bestOpponentAttack")

        score = th * 100

        # Hit but not tripled = cleanup priority
        if best:
            stars = best.get("stars", 0)
            destruction = best.get("destructionPercentage", 0)

            if stars == 2:
                score += 250
                if destruction >= 85:
                    score += 80
            elif stars == 1:
                score += 180
                if destruction >= 70:
                    score += 40
            elif stars == 0:
                score += 60
                if destruction >= 50:
                    score += 20
        else:
            # untouched high bases still matter
            if th >= 17:
                score += 140
            elif th >= 15:
                score += 80

        # top of map gets slight bias
        score += max(0, 30 - pos)

        # comeback mode: heavily value high TH cleanup/triples
        if strategy == "comeback":
            score += th * 15

        return score

    def needs_cleanup(target):
        best = target.get("bestOpponentAttack")
        if not best:
            return False

        stars = best.get("stars", 0)
        destruction = best.get("destructionPercentage", 0)
        th = target.get("townhallLevel") or 0

        # obvious cleanup conditions
        if stars == 2:
            return True
        if stars == 1 and destruction >= 70:
            return True

        # late war or comeback: even some 0/1 star hits become cleanup candidates
        if phase == "late" and strategy in ("balanced", "comeback"):
            if stars == 1:
                return True
            if stars == 0 and destruction >= 75:
                return True

        # very high bases can justify cleanup even on moderate damage
        if th >= 17 and stars >= 1:
            return True

        return False

    def is_high_priority(target):
        th = target.get("townhallLevel") or 0
        pos = target.get("mapPosition") or 99
        best = target.get("bestOpponentAttack")

        if best and best.get("stars", 0) == 2:
            return True

        if th >= 17:
            return True

        if strategy == "comeback" and th >= 15:
            return True

        if phase == "late" and pos <= 3:
            return True

        return False

    sorted_attackers = sorted(
        clan_members,
        key=lambda m: ((m.get("townhallLevel") or 0), player_score(m)),
        reverse=True,
    )

    # Sort targets by priority instead of only TH
    prioritized_targets = sorted(
        opponent_members,
        key=lambda t: (target_priority(t), -(t.get("townhallLevel") or 0)),
        reverse=True,
    )

    assigned_primary_targets = set()

# ---------------- PASS 1: PRIMARY ONLY ----------------

    for target in prioritized_targets:
        pos = target.get("mapPosition")

        if already_tripled(target):
            continue

        candidates = [
            m
            for m in sorted_attackers
            if can_use_player(m.get("name"))
            and not already_hit_target(m, target)
            and is_eligible(m, target, allow_desperation=False)
        ]

        if not candidates:
            candidates = [
                m
                for m in sorted_attackers
                if can_use_player(m.get("name"))
                and not already_hit_target(m, target)
                and is_eligible(m, target, allow_desperation=True)
            ]

        if not candidates:
            continue

        candidates = sorted(
            candidates,
            key=lambda m: attacker_score(m, target),
            reverse=True,
        )

        primary = candidates[0]
        name = primary.get("name")

        player_usage[name] = player_usage.get(name, 0) + 1
        assigned_primary_targets.add(pos)

        assignments.append(
            {
                "player": name,
                "primary": pos,
                "backup": [],
                "confidence": 85,
                "label": "primary",
            }
        )
        suggestions.append(f"{name} → #{pos} (primary)")

# ---------------- PASS 2: CLEANUP ONLY WHEN NEEDED ----------------

    for target in prioritized_targets:
        pos = target.get("mapPosition")

        if pos not in assigned_primary_targets:
            continue

        if already_tripled(target):
            continue

        if not (needs_cleanup(target) or is_high_priority(target)):
            continue

        # Don't add duplicate cleanup if somehow already assigned
        already_on_target = {a["player"] for a in assignments if a["primary"] == pos}

        candidates = [
            m
            for m in sorted_attackers
            if can_use_player(m.get("name"))
            and m.get("name") not in already_on_target
            and not already_hit_target(m, target)
            and is_eligible(m, target, allow_desperation=False)
        ]

        if not candidates and phase == "late":
            candidates = [
                m
                for m in sorted_attackers
                if can_use_player(m.get("name"))
                and m.get("name") not in already_on_target
                and not already_hit_target(m, target)
                and is_eligible(m, target, allow_desperation=False)
            ]

        if not candidates:
            continue

        candidates = sorted(
            candidates,
            key=lambda m: attacker_score(m, target),
            reverse=True,
        )

        cleanup = candidates[0]
        name = cleanup.get("name")

        player_usage[name] = player_usage.get(name, 0) + 1

        confidence = 72
        if needs_cleanup(target):
            confidence += 8
        if is_high_priority(target):
            confidence += 5

        assignments.append(
            {
                "player": name,
                "primary": pos,
                "backup": [],
                "confidence": min(confidence, 90),
                "label": "cleanup",
            }
        )
        suggestions.append(f"{name} → #{pos} (cleanup)")

# ---------------- HIT ORDER ----------------

    hit_order = [m.get("name") for m in sorted_attackers]

# ---------------- MVP PREDICTION ----------------

    mvp_scores = {}
    for a in assignments:
        player = a["player"]
        score = a.get("confidence", 50)
        if a.get("label") == "cleanup":
            score += 10
        mvp_scores[player] = mvp_scores.get(player, 0) + score

    predicted_mvp = max(mvp_scores, key=mvp_scores.get) if mvp_scores else None

# ---------------- WIN PREDICTOR ----------------

    clan_attacks = clan.get("attacks", 0)
    opp_attacks = opponent.get("attacks", 0)
    total_attacks = war.get("teamSize", 0) * war.get("attacksPerMember", 2)

    clan_efficiency = clan_stars / clan_attacks if clan_attacks else 0
    opp_efficiency = opp_stars / opp_attacks if opp_attacks else 0

    projected_clan = clan_stars + ((total_attacks - clan_attacks) * clan_efficiency)
    projected_opp = opp_stars + ((total_attacks - opp_attacks) * opp_efficiency)

    win_chance = (
        min(90, 50 + (projected_clan - projected_opp) * 5)
        if projected_clan > projected_opp
        else max(10, 50 - (projected_opp - projected_clan) * 5)
    )

# ---------------- CAPTAIN CALLS ----------------

    captain_lines = []
    if phase == "early":
        captain_lines.append(
            "Single primary assignments first. Save 2nd attack for cleanup."
        )
    elif phase == "mid":
        captain_lines.append(
            "Use primaries first, then focus cleanup on failed high-value hits."
        )
    else:
        captain_lines.append("Prioritize triples and key cleanup only.")

    if strategy == "comeback":
        captain_lines.append(
            "We need efficient triples. Cleanup only where it can swing stars."
        )
    elif strategy == "secure":
        captain_lines.append("Protect the lead. Clean only high-value misses.")

    if predicted_mvp:
        captain_lines.append(f"MVP Prediction: {predicted_mvp}")

    if not clan_members or not opponent_members:
        return {
            "suggestions": [],
            "assignments": [],
            "hit_order": [],
            "phase": "N/A",
            "strategy": "N/A",
            "captain_calls": ["No active war"],
            "win_chance": 0,
            "mvp": None,
        }

    return {
        "suggestions": suggestions[:20],
        "assignments": assignments,
        "hit_order": hit_order,
        "phase": phase,
        "strategy": strategy,
        "captain_calls": captain_lines,
        "win_chance": round(win_chance, 1),
        "mvp": predicted_mvp,
    }

async def process_war_updates(war, members, clan_tag: str, is_main_clan: bool = False):
    """Main war update dispatcher for AMA and feeder clans."""

    # Post/update the same current-war render for every configured clan.
    # Main clan keeps the original message/state files; feeder gets scoped files.
    await update_war_dashboard(war, members, clan_tag=clan_tag)

    # Both clans can generate clutch moments. Clutch files are already scoped by clan tag.
    await process_clutch_attacks(war)

    # Both clans should earn war-end rewards and get a war summary/MVP post.
    if war.get("state") == "warEnded":
        war_rewards = await reward_war_coins(war)
        await update_monthly_mvp_from_war(war)
        await post_final_war_summary(war, war_rewards=war_rewards)
    
# ---------------- UPDATE LOOP ----------------

@tasks.loop(minutes=2)
async def update_loop():
    await run_update_cycle(
        bot=bot,
        clan_tags=CLAN_TAGS,
        main_clan_tag=MAIN_CLAN_TAG,
        clan_stats_channel_id=CLAN_STATS_CHANNEL_ID,
        fetch_clan_data=fetch_clan_data,
        update_donation_leaderboard=donation_update,
        process_war_updates=process_war_updates,
    ) 
        
# ---------------- LOOT DROP LOOP ----------------
        
@tasks.loop(minutes=1)
async def loot_drop_loop():
    try:
        drop = await load_loot_drop()

        if drop.get("active"):
            return

        next_drop_at_raw = drop.get("next_drop_at")

        if not next_drop_at_raw:
            await schedule_next_loot_drop()
            return

        next_drop_at = datetime.fromisoformat(next_drop_at_raw)
        now = datetime.now(timezone.utc)

        if now >= next_drop_at:
            await create_loot_drop()

    except Exception as e:
        print(f"[LOOT DROP LOOP ERROR] {e}")
        traceback.print_exc()

# ---------------- SESSION REFRESH ----------------

@tasks.loop(hours=6)
async def refresh_session():
    print("🔄 Refreshing HTTP session...")
    await close_session()
    await get_session()

# ---------------- WAR DASHBOARD UPDATER ----------------

async def update_war_dashboard(war, full_members, clan_tag: str | None = None):
    clan_tag = normalize_tag(clan_tag or war.get("clan", {}).get("tag", "") or MAIN_CLAN_TAG)
    channel = bot.get_channel(war_channel_id_for_clan(clan_tag))
    if not channel:
        return

    ended_file = scoped_state_file(WAR_END_FILE, clan_tag)
    war_message_file = scoped_state_file(WAR_MESSAGE_FILE, clan_tag)
    ended_data = await safe_load_json(ended_file)
    state = war.get("state", "N/A")
    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    if state != "warEnded" and ended_data.get("posted"):
        await safe_save_json(ended_file, {"posted": False})
        await reset_war_pings(clan_tag)
        ended_data = {"posted": False}

    mid = await get_saved_message(war_message_file)
    war_msg = None
    if mid:
        try:
            war_msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            war_msg = None

    # If war is already over, final summary was posted, and the dashboard message
    # still exists, skip rebuilding the dashboard every loop.
    if state == "warEnded" and ended_data.get("posted") and war_msg is not None:
        return

# ---------------- LIVE WAR VS ENDED WAR ----------------
    
    if state == "warEnded":
        # No AI suggestions after war ends
        data = {
            "mvp": None,
            "assignments": [],
            "hit_order": [],
            "captain_calls": [],
            "suggestions": [],
            "phase": "ended",
            "strategy": "ended",
            "win_chance": 0,
        }
    else:
        data = await generate_attack_suggestions(war)

    buffer = await create_war_image(war, data)
    file = discord.File(fp=buffer, filename="war.png")

    embed = discord.Embed(color=0x2C2F33)
    embed.set_image(url="attachment://war.png")

    if war_msg:
        try:
            # Normal path: edit the existing dashboard message for this clan.
            # This prevents the 2-minute loop from spamming new posts.
            await war_msg.edit(embeds=[embed], attachments=[file])
        except discord.HTTPException as e:
            # Do not create a new message on transient edit errors. The saved
            # message ID remains in place, so the next loop will retry the edit.
            print(f"[WAR DASHBOARD EDIT ERROR] {clan_tag}: {e}")
    else:
        # Only post a new dashboard if the saved message ID is missing or the
        # message was deleted/unfetchable. Each clan has its own message-ID file.
        new_msg = await asyncio.wait_for(
            channel.send(embed=embed, file=file), timeout=10
        )
        await save_message(war_message_file, new_msg.id)

# ---------------- FINAL WAR IMAGE (RUN ONCE) ----------------
    if state == "warEnded" and not ended_data.get("posted"):
        await safe_save_json(ended_file, {"posted": True})

# ---------------- CHECK WAR PINGS ----------------

    await check_war_pings(war, clan_tag=clan_tag)
    await check_unlinked_players(war, clan_tag=clan_tag)

# ---------------- WAR PINGS ----------------

async def ping_users_for_interval(interval, members, attacks_per_member, clan_tag: str | None = None):
    linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
    channel = bot.get_channel(war_channel_id_for_clan(clan_tag))
    if not channel:
        return

    war_pings_file = scoped_state_file(WAR_PINGS_FILE, clan_tag)
    current_pings = await safe_load_json(war_pings_file)
    already_pinged = set(current_pings.get(interval, []))
    messages = []
    new_user_ids = []

    for m in members:
        used_attacks = len(m.get("attacks", []))
        if used_attacks >= attacks_per_member:
            continue

        member_tag = normalize_tag(m.get("tag", ""))
        if not member_tag:
            continue
        
        for user_id, tags in linked.items():
            if not isinstance(tags, list):
                tags = [tags]
        
            normalized_tags = []
            for entry in tags:
                if isinstance(entry, dict):
                    tag_value = entry.get("tag")
                elif isinstance(entry, str):
                    tag_value = entry
                else:
                    tag_value = None
        
                if tag_value and isinstance(tag_value, str):
                    normalized_tags.append(normalize_tag(tag_value))
        
            if member_tag in normalized_tags:
                if user_id not in already_pinged and user_id not in new_user_ids:
                    mention = f"<@{user_id}>"
                    if mention not in messages:
                        messages.append(mention)
                    new_user_ids.append(user_id)

    if messages:
        if interval == "start":
            msg = f"⚔️ **War has started!**\nYou have {attacks_per_member} attacks.\n{' '.join(messages)}"
        elif interval == "12h":
            msg = f"⚠️ **War Reminder (12h remaining)**\nPlayers missing attacks:\n{' '.join(messages)}"
        elif interval == "1h":
            msg = f"🚨 **FINAL WAR REMINDER (1h remaining)**\nPlayers still missing attacks:\n{' '.join(messages)}"
        elif interval == "end":
            msg = f"⏳ **War ending in 5 minutes!**\nLast chance to attack!\n{' '.join(messages)}"
        else:
            msg = None

        if msg:
            await asyncio.wait_for(channel.send(msg, delete_after=3600), timeout=10)

    if new_user_ids:

        def _update_pings(data):
            if interval not in data:
                data[interval] = []

            existing = set(data[interval])
            for user_id in new_user_ids:
                if user_id not in existing:
                    data[interval].append(user_id)
                    existing.add(user_id)

            return data

        await update_json_file(war_pings_file, _update_pings)


async def check_war_pings(war, clan_tag: str | None = None):
    end_time = war.get("endTime")
    start_time = war.get("startTime")
    if not end_time:
        return

    now = datetime.now(timezone.utc)
    end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(
        tzinfo=timezone.utc
    )
    start_dt = (
        datetime.strptime(start_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        if start_time
        else None
    )

    members = war.get("clan", {}).get("members", [])
    attacks_per_member = war.get("attacksPerMember", 2)
    time_left = end_dt - now

    if start_dt and timedelta(seconds=0) <= (now - start_dt) < timedelta(minutes=10):
        await ping_users_for_interval("start", members, attacks_per_member, clan_tag=clan_tag)

    if timedelta(hours=11, minutes=50) <= time_left <= timedelta(hours=12, minutes=10):
        await ping_users_for_interval("12h", members, attacks_per_member, clan_tag=clan_tag)

    if timedelta(minutes=50) <= time_left <= timedelta(hours=1, minutes=10):
        await ping_users_for_interval("1h", members, attacks_per_member, clan_tag=clan_tag)

    if timedelta(seconds=0) <= time_left <= timedelta(minutes=10):
        await ping_users_for_interval("end", members, attacks_per_member, clan_tag=clan_tag)

async def check_unlinked_players(war, clan_tag: str | None = None):
    members = war.get("clan", {}).get("members", [])
    linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
    warned_file = scoped_state_file(UNLINKED_WARN_FILE, clan_tag)
    warned = await safe_load_json(warned_file)

    channel = bot.get_channel(war_channel_id_for_clan(clan_tag))
    if not channel:
        return

    linked_tags = set()
    for entries in linked.values():
        for entry in entries:
            tag = entry.get("tag")
            if tag:
                linked_tags.add(normalize_tag(tag))

    new_warnings = []
    tags_to_mark = []

    for m in members:
        tag = normalize_tag(m.get("tag", ""))
        name = m.get("name", "Unknown")

        if tag and tag not in linked_tags and tag not in warned:
            new_warnings.append(f"{name} ({tag})")
            tags_to_mark.append(tag)

    if new_warnings:
        msg = (
            "⚠️ **The following war members have NOT linked their Discord:**\n\n"
            + "\n".join(f"• {n}" for n in new_warnings)
            + "\n\nPlease run `/link` to enable war reminders."
        )
        await asyncio.wait_for(channel.send(msg, delete_after=3600), timeout=10)

    if tags_to_mark:

        def _update_warned(data):
            for tag in tags_to_mark:
                data[tag] = True
            return data

        await update_json_file(warned_file, _update_warned)

# ---------------- LINK AUDIT COMMAND ----------------


from types import SimpleNamespace

command_context = SimpleNamespace(**{
    name: globals()[name]
    for name in [
        "LEADER_ROLE_ID", "CO_LEADER_ROLE_ID", "CLAN_CHAT_CHANNEL_ID",
        "LOOT_DROP_FILE", "SHOP_ITEMS", "LOOT_DROP_STYLES", "LINKED_FILE", "COIN_LEADERBOARD_IMAGE_PATH",
        "CLAN_TAGS", "MAIN_CLAN_TAG", "TAG_REGEX", "WAR_CHANNEL_ID", "FEEDER_WAR_CHANNEL_ID",
        "safe_load_json", "safe_save_json", "update_json_file",
        "normalize_tag", "normalize_linked_data", "build_tag_to_discord_map",
        "load_coins", "load_shop_data", "spend_coins", "add_shop_item", "consume_shop_item", "equip_shop_item", "activate_shop_effect", "get_active_shop_effects", "steal_coins", "get_inventory_text",
        "create_loot_drop", "load_loot_drop", "schedule_next_loot_drop",
        "fetch_clan_data", "get_cached_or_fetch",
    ]
    if name in globals()
})
register_all_commands(bot, command_context)

# linkaudit moved to commands package.
        
# ---------------- SPAWN LOOT COMMAND ----------------

# spawnloot moved to commands package.
    
# ---------------- BALANCE COMMAND ----------------
        
# balance moved to commands package.


# create_coin_leaderboard_image moved to commands package.

# ---------------- COIN LEADERBOARD COMMAND ----------------

# coinleaderboard moved to commands package.

# ---------------- DROP STATUS COMMAND ----------------

# dropstatus moved to commands package.
    
# ---------------- RESET DROP COMMAND ----------------
    
# resetdrop moved to commands package.
    
# ---------------- LINKED COMMAND ----------------

# linked moved to commands package.
    
# ---------------- LINK COMMAND ----------------
    
# link moved to commands package.

# ---------------- UNLINK COMMAND ----------------

# unlink moved to commands package.

# ---------------- SHOP COMMAND ----------------

# shop moved to commands package.
    
# ---------------- BUY COMMAND ----------------

# buy moved to commands package.
    
# buy_item_autocomplete moved to commands package.
    
# ---------------- INVENTORY COMMAND ----------------

# inventory moved to commands package.

# ---------------- COMMAND ERROR ----------------

@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    print(f"[APP COMMAND ERROR] {error}")
    traceback.print_exc()

    try:
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Something went wrong while running that command.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Something went wrong while running that command.",
                ephemeral=True,
            )
    except Exception as followup_error:
        print(f"[APP COMMAND ERROR HANDLER FAILED] {followup_error}")

# ---------------- BOT EVENTS ----------------

@bot.event
async def on_ready():
    global api_cache
    api_cache = await load_cache()
    await get_session()
    print(f"Bot logged in as {bot.user}")
    await tree.sync()

    if not update_loop.is_running():
        update_loop.start()

    if not loot_drop_loop.is_running():
        loot_drop_loop.start()
        
    drop = await load_loot_drop()
    if not drop.get("active") and not drop.get("next_drop_at"):
        await schedule_next_loot_drop()

    if not refresh_session.is_running():
        refresh_session.start()
        
@bot.event
async def on_message(message: discord.Message):
    try:
        handled = await claim_loot_drop(message)
        if handled:
            return
    except Exception as e:
        print(f"[ON MESSAGE ERROR] {e}")
        traceback.print_exc()

# Safe shutdown function
async def shutdown():
    print("Shutdown signal received...")
    await bot.close()

# ---------------- SAFE MESSAGE HELPERS ----------------

async def get_saved_message(path):
    """Return saved message ID from file, or None."""
    async with file_lock:
        if not os.path.exists(path):
            return None

        def _read():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return int(f.read().strip())
            except Exception:
                return None

        return await asyncio.to_thread(_read)

async def save_message(path, message_id):
    """Save message ID to file."""
    async with file_lock:

        def _write():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(message_id))
            except Exception as e:
                print(f"Error saving message ID to {path}: {e}")

        await asyncio.to_thread(_write)

# ---------------- RUN BOT ----------------

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    bot.run(DISCORD_TOKEN)
