# ---------------- ENVIRONMENT ----------------

import os
import json
import html as html_lib
import aiohttp
import asyncio
import signal
import re
import traceback
import random
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from playwright.async_api import async_playwright
from upgrade_advisor import register_upgrade_advisor
from commands import register_all_commands
from economy import EconomyManager
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
import discord
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv

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
    clan = war.get("clan") or {}
    clan_tag = normalize_tag(clan.get("tag", ""))
    if not clan_tag:
        return None
    return clan_tag.replace("#", "")


def get_clutch_log_file(war):
    scope_key = get_clutch_scope_key(war)
    if not scope_key:
        return None
    return os.path.join(DATA_DIR, f"clutch_log_{scope_key}.json")


def get_clutch_state_file(war):
    scope_key = get_clutch_scope_key(war)
    if not scope_key:
        return None
    return os.path.join(DATA_DIR, f"clutch_state_{scope_key}.json")

TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$")
HEADERS = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}

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
        await super().close()

bot = ClanBot(command_prefix="/", intents=intents)
tree = bot.tree

# ---------------- GLOBALS/COOLDOWNS ----------------

session: aiohttp.ClientSession | None = None
api_cache = {}
file_lock = asyncio.Lock()
loot_drop_lock = asyncio.Lock()

economy = EconomyManager(
    coins_file=COINS_FILE,
    shop_file=SHOP_FILE,
    linked_file=LINKED_FILE,
    shop_items=SHOP_ITEMS,
    star_coin_reward=STAR_COIN_REWARD,
    war_mvp_bonus=WAR_MVP_BONUS,
    clutch_coin_reward=CLUTCH_COIN_REWARD,
    clutch_reward_tiers=CLUTCH_REWARD_TIERS,
    advisor_progress_rewards=ADVISOR_PROGRESS_REWARDS,
    advisor_group_rewards=ADVISOR_GROUP_REWARDS,
    advisor_sync_reward=ADVISOR_DAILY_SYNC_REWARD,
)

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
    return f"{normalize_tag(member_tag)}_{normalize_tag(attack.get('defenderTag', ''))}_{attack.get('order', 0)}"


def collect_clan_attacks(war):
    attacks = []
    for member in war.get("clan", {}).get("members", []):
        member_tag = member.get("tag", "")
        member_name = member.get("name", "Someone")
        for attack in member.get("attacks", []):
            attacks.append(
                {
                    "member_tag": member_tag,
                    "member_name": member_name,
                    "attack": attack,
                    "order": attack.get("order", 0),
                    "defender_tag": normalize_tag(attack.get("defenderTag", "")),
                    "stars": attack.get("stars", 0) or 0,
                    "destruction": attack.get("destructionPercentage", 0) or 0,
                }
            )
    attacks.sort(key=lambda x: x["order"])
    return attacks


def get_prior_best_on_defender(war, defender_tag, attack_order):
    defender_tag = normalize_tag(defender_tag)
    best_stars = 0
    best_destruction = 0

    for item in collect_clan_attacks(war):
        if item["order"] >= attack_order:
            break
        if item["defender_tag"] != defender_tag:
            continue

        stars = item["stars"]
        destruction = item["destruction"]
        if stars > best_stars or (stars == best_stars and destruction > best_destruction):
            best_stars = stars
            best_destruction = destruction

    return {"stars": best_stars, "destruction": best_destruction}


def classify_war_state(star_diff, destruction_diff):
    if star_diff > 0:
        return "winning"
    if star_diff < 0:
        return "losing"
    if destruction_diff > 0:
        return "winning"
    if destruction_diff < 0:
        return "losing"
    return "tied"


def get_attack_impact(attack, war):
    defender_tag = attack.get("defenderTag", "")
    attack_order = attack.get("order", 0)
    new_stars = attack.get("stars", 0) or 0
    new_destruction = attack.get("destructionPercentage", 0) or 0
    prior_best = get_prior_best_on_defender(war, defender_tag, attack_order)

    star_gain = max(0, new_stars - prior_best["stars"])
    destruction_gain = 0
    if new_stars > prior_best["stars"]:
        destruction_gain = new_destruction
    elif new_stars == prior_best["stars"] and new_destruction > prior_best["destruction"]:
        destruction_gain = new_destruction - prior_best["destruction"]

    return {
        "prior_best_stars": prior_best["stars"],
        "prior_best_destruction": prior_best["destruction"],
        "star_gain": star_gain,
        "destruction_gain": destruction_gain,
        "is_new_triple": new_stars == 3 and prior_best["stars"] < 3,
    }


def is_clutch_attack(attack, war, attacker_tag=None):
    try:
        end_time = war.get("endTime")
        if not end_time:
            return None

        now = datetime.utcnow()
        war_end = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z")
        time_left_seconds = (war_end - now).total_seconds()
        if time_left_seconds < 0:
            return None

        defender_pos = get_defender_position(attack, war)
        attacker_pos = get_attacker_position(attack, war, attacker_tag=attacker_tag)
        attacker_th = get_attacker_townhall_level(attack, war, attacker_tag=attacker_tag)
        defender_th = get_defender_townhall_level(attack, war)
        impact = get_attack_impact(attack, war)
        if impact["star_gain"] <= 0 and impact["destruction_gain"] <= 0:
            return None

        clan = war.get("clan", {})
        opponent = war.get("opponent", {})

        clan_stars_after = clan.get("stars", 0) or 0
        clan_destruction_after = float(clan.get("destructionPercentage", 0) or 0)
        opponent_stars = opponent.get("stars", 0) or 0
        opponent_destruction = float(opponent.get("destructionPercentage", 0) or 0)

        clan_stars_before = clan_stars_after - impact["star_gain"]
        clan_destruction_before = clan_destruction_after - impact["destruction_gain"]

        before_state = classify_war_state(
            clan_stars_before - opponent_stars,
            clan_destruction_before - opponent_destruction,
        )
        after_state = classify_war_state(
            clan_stars_after - opponent_stars,
            clan_destruction_after - opponent_destruction,
        )

        stars = attack.get("stars", 0) or 0
        is_new_triple = impact["is_new_triple"]
        th_gap = None
        if attacker_th is not None and defender_th is not None:
            th_gap = int(defender_th) - int(attacker_th)

        # Highest impact checks first so the rarest moments win priority.
        if (
            0 <= time_left_seconds <= 3600
            and is_new_triple
            and before_state != after_state
            and after_state in {"tied", "winning"}
        ):
            return "lead_flip"

        if (
            0 <= time_left_seconds <= 1800
            and is_new_triple
            and (clan_stars_after - opponent_stars) >= -1
            and (clan_stars_before - opponent_stars) <= -2
        ):
            return "keep_alive"

        if (
            0 <= time_left_seconds <= 900
            and stars == 3
            and is_new_triple
            and impact["prior_best_stars"] >= 2
        ):
            return "last_stand"

        if is_new_triple and th_gap is not None and th_gap >= 1:
            return "underdog_triple"

        if is_new_triple and defender_pos is not None and defender_pos <= 3:
            return "top_three_triple"

        if (
            is_new_triple
            and defender_pos is not None
            and defender_pos <= 5
            and attacker_pos is not None
            and (attacker_pos - defender_pos) >= 5
        ):
            return "rank_upset"

        if (
            defender_pos is not None
            and defender_pos <= 3
            and is_new_triple
            and (
                abs(clan_stars_before - opponent_stars) <= 3
                or 0 <= time_left_seconds <= 21600
            )
        ):
            return "top_base"

        return None

    except Exception as e:
        print(f"[CLUTCH CHECK ERROR] {e}")
        traceback.print_exc()
        return None



async def post_clutch_moment(attack, war, attacker_tag, attacker_name, attack_id, clutch_type=None):
    channel = bot.get_channel(CLAN_CHAT_CHANNEL_ID)
    if not channel:
        return

    defender_pos = get_defender_position(attack, war)
    defender_pos_display = defender_pos if defender_pos is not None else "?"
    clan_name = war.get("clan", {}).get("name", "Clan")
    mention = await resolve_discord_mention(attacker_tag, attacker_name)

    messages = {
        "top_base": [
            f"\U0001F6A8 **{clan_name} WAR SWING**\n\n{mention} just tripled #{defender_pos_display} \U0001F624\U0001F525",
            f"\U0001F525 **{clan_name} BIG HIT**\n\n{mention} demolished #{defender_pos_display} — huge for us",
        ],
        "lead_flip": [
            f"\U0001F4C8 **{clan_name} MOMENTUM SHIFT**\n\n{mention} just flipped the war with that hit on #{defender_pos_display} \U0001F440\U0001F525",
            f"\U0001F6A8 **{clan_name} CLUTCH SWING**\n\n{mention} just changed the war math on #{defender_pos_display} \U0001F624",
        ],
        "keep_alive": [
            f"\U0001FAC0 **{clan_name} STILL ALIVE**\n\n{mention} kept us in this war with a huge triple on #{defender_pos_display} \U0001F525",
            f"\u2694\ufe0f **{clan_name} COMEBACK HIT**\n\n{mention} just pulled us right back into it on #{defender_pos_display}",
        ],
        "last_stand": [
            f"\u23F0 **{clan_name} LAST STAND**\n\n{mention} cleaned up #{defender_pos_display} when it mattered most \U0001F440\U0001F525",
            f"\U0001F6A8 **{clan_name} LAST SECOND HERO**\n\n{mention} just saved that base at the buzzer \U0001F624",
        ],
        "top_three_triple": [
            f"\U0001F3AF **{clan_name} STATEMENT HIT**\n\n{mention} just tripled one of their top bases — #{defender_pos_display} got smoked \U0001F525",
            f"\U0001F4A5 **{clan_name} ELITE TRIPLE**\n\n{mention} took down enemy #{defender_pos_display} like it was light work \U0001F624",
        ],
        "underdog_triple": [
            f"\U0001F199 **{clan_name} UPSET ALERT**\n\n{mention} punched up and tripled #{defender_pos_display} \U0001F440\U0001F525",
            f"\u26A1 **{clan_name} TOWN HALL UPSET**\n\n{mention} just outclassed a stronger base at #{defender_pos_display}",
        ],
        "rank_upset": [
            f"\U0001F94A **{clan_name} REACH HIT**\n\n{mention} just took down a base above their rank — #{defender_pos_display} got folded \U0001F525",
            f"\U0001F680 **{clan_name} CLUTCH UPSET**\n\n{mention} reached up and buried #{defender_pos_display} \U0001F624",
        ],
    }
    clutch_type = clutch_type or is_clutch_attack(attack, war)
    if not clutch_type:
        return

    reward_result = await reward_clutch_coins(attacker_tag, attacker_name, attack_id, clutch_type=clutch_type)
    if reward_result and reward_result.get("ok"):
        reward_amount = int(reward_result.get("reward", 0) or 0)
        msg = random.choice(messages.get(clutch_type, [f"\U0001F525 **{clan_name} HUGE HIT**\n\n{mention} came through big on #{defender_pos_display}"])) + f"\n\n\U0001F4B0 +{reward_amount} coins"
    else:
        failure_reason = (reward_result or {}).get("reason", "unknown")
        print(
            f"[CLUTCH] Reward skipped for {attacker_name} ({normalize_tag(attacker_tag or '')}) "
            f"attack_id={attack_id} reason={failure_reason}"
        )
        msg = random.choice(messages.get(clutch_type, [f"\U0001F525 **{clan_name} HUGE HIT**\n\n{mention} came through big on #{defender_pos_display}"]))
        if failure_reason == "unlinked":
            msg += "\n\n⚠️ No linked Discord account found, so no coins were awarded."
        elif failure_reason == "duplicate":
            msg += "\n\n♻️ This clutch hit was already rewarded earlier."

    await channel.send(msg)


async def post_clutch_summary(war, clutch_hits):
    channel = bot.get_channel(CLAN_CHAT_CHANNEL_ID)
    if not channel or not clutch_hits:
        return

    clan_name = war.get("clan", {}).get("name", "Clan")
    lines = []

    reason_labels = {
        "top_base": "top base",
        "top_three_triple": "enemy top 3 triple",
        "underdog_triple": "town hall upset",
        "rank_upset": "reach triple",
        "lead_flip": "war swing",
        "keep_alive": "kept us alive",
        "last_stand": "late cleanup",
    }

    for hit in clutch_hits[:5]:
        defender_pos = get_defender_position(hit["attack"], war)
        defender_pos_display = defender_pos if defender_pos is not None else "?"
        reason = reason_labels.get(hit.get("clutch_type"), "clutch hit")
        reward_amount = get_clutch_reward_amount(hit.get("clutch_type"))
        lines.append(f"• {hit['attacker_name']} tripled #{defender_pos_display} ({reason}, +{reward_amount} coins)")

    extra_count = len(clutch_hits) - len(lines)
    extra_line = f"\n…and {extra_count} more." if extra_count > 0 else ""

    msg = (
        f"\U0001F525 **{clan_name} CLUTCH RECAP**\n\n"
        f"Detected {len(clutch_hits)} new clutch hits since the last check, so I bundled them instead of spamming the chat.\n\n"
        + "\n".join(lines)
        + extra_line
    )
    await channel.send(msg)


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
        await post_clutch_summary(war, new_clutch_hits)
        for hit in new_clutch_hits:
            await reward_clutch_coins(hit["attacker_tag"], hit["attacker_name"], hit["attack_id"], clutch_type=hit["clutch_type"])
            new_log.add(hit["attack_id"])
    else:
        for hit in new_clutch_hits:
            await post_clutch_moment(
                hit["attack"],
                war,
                hit["attacker_tag"],
                hit["attacker_name"],
                hit["attack_id"],
                hit["clutch_type"],
            )
            new_log.add(hit["attack_id"])

    await safe_save_json(log_file, list(new_log | current_attack_ids))
    await safe_save_json(
        state_file,
        {"war_signature": war_signature, "initialized": True},
    )
# ---------------- CACHE SYSTEM ----------------

CACHE_FILE = os.path.join(DATA_DIR, "api_cache.json")

async def load_cache():
    return await safe_load_json(CACHE_FILE)

async def save_cache(cache):
    await safe_save_json(CACHE_FILE, cache)

async def get_cached_or_fetch(key, url, ttl=120):
    global api_cache
    now = datetime.now(timezone.utc).timestamp()

    if key in api_cache:
        entry = api_cache[key]
        if now - entry.get("timestamp", 0) < ttl:
            return entry.get("data")

    try:
        data = await asyncio.wait_for(fetch_json(url), timeout=10)
    except asyncio.TimeoutError:
        print(f"[CACHE TIMEOUT] Using stale data for {key}")
        return api_cache.get(key, {}).get("data")

    if data is not None:
        api_cache[key] = {
            "timestamp": now,
            "ttl": ttl,
            "data": data,
        }

        if len(api_cache) > 100:
            api_cache = dict(
                sorted(
                    api_cache.items(),
                    key=lambda item: item[1].get("timestamp", 0),
                    reverse=True,
                )[:100]
            )

        await save_cache(api_cache)

    return data
    
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

async def load_performance():
    return await safe_load_json(PERFORMANCE_FILE)
    
def get_season_key():
    return datetime.now(timezone.utc).strftime("%Y-%m")

def get_war_id(war):
    clan_tag = war.get("clan", {}).get("tag", "")
    opponent_tag = war.get("opponent", {}).get("tag", "")
    end_time = war.get("endTime", "")
    prep_time = war.get("preparationStartTime", "")
    team_size = war.get("teamSize", 0)
    return f"{clan_tag}_{opponent_tag}_{team_size}_{prep_time}_{end_time}"

def get_war_mvp_stats(war):
    clan = war.get("clan", {})
    best_member = None
    best_score = -1

    for member in clan.get("members", []):
        attacks = member.get("attacks", [])
        if not attacks:
            continue

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        triples = sum(1 for a in attacks if a.get("stars", 0) == 3)
        attack_count = len(attacks)
        score = stars * 100 + destruction

        if score > best_score:
            best_score = score
            best_member = {
                "name": member.get("name", "Unknown"),
                "tag": member.get("tag", ""),
                "stars": stars,
                "destruction": round(destruction, 2),
                "triples": triples,
                "attacks": attack_count,
                "score": round(score, 2),
            }

    return best_member

async def update_monthly_mvp_from_war(war):
    if war.get("state") != "warEnded":
        return

    season_key = get_season_key()
    war_id = get_war_id(war)
    clan = war.get("clan", {})

    def _update_mvp(stored):
        if not isinstance(stored, dict):
            stored = {}

        if stored.get("season") != season_key:
            stored = {
                "season": season_key,
                "wars": [],
                "players": {}
            }

        processed_wars = stored.setdefault("wars", [])
        players = stored.setdefault("players", {})

        if war_id in processed_wars:
            return stored

        for member in clan.get("members", []):
            name = member.get("name")
            if not name:
                continue

            attacks = member.get("attacks", [])
            if not attacks:
                continue

            stars = sum(a.get("stars", 0) for a in attacks)
            destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
            attack_count = len(attacks)
            triples = sum(1 for a in attacks if a.get("stars") == 3)
            score = stars * 100 + destruction

            players.setdefault(
                name,
                {
                    "points": 0,
                    "wars": 0,
                    "attacks": 0,
                    "stars": 0,
                    "destruction": 0,
                    "triples": 0,
                }
            )

            players[name]["points"] += round(score, 2)
            players[name]["wars"] += 1
            players[name]["attacks"] += attack_count
            players[name]["stars"] += stars
            players[name]["destruction"] += round(destruction, 2)
            players[name]["triples"] += triples

        processed_wars.append(war_id)
        return stored

    await update_json_file(MONTHLY_MVP_FILE, _update_mvp)

async def post_war_mvp_announcement(war, channel: discord.abc.Messageable | None = None, war_rewards=None):
    target_channel = channel or bot.get_channel(CLAN_CHAT_CHANNEL_ID)
    if not target_channel:
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    clan_name = clan.get("name", "Our Clan")
    opponent_name = opponent.get("name", "Opponent")

    best_member = get_war_mvp_stats(war)
    if not best_member:
        return

    mvp_reward = None
    if isinstance(war_rewards, dict):
        mvp_reward = war_rewards.get("mvp")

    if not mvp_reward:
        fallback_rewards = await reward_war_coins(war)
        if isinstance(fallback_rewards, dict):
            mvp_reward = fallback_rewards.get("mvp")

    mvp_display = format_member_mention(
        (mvp_reward or {}).get("discord_id"),
        best_member.get("name", "Unknown"),
    )
    mvp_total_reward = int((mvp_reward or {}).get("total_reward", 0))

    clan_stars = clan.get("stars", 0)
    opp_stars = opponent.get("stars", 0)
    clan_destruction = clan.get("destructionPercentage", 0)
    opp_destruction = opponent.get("destructionPercentage", 0)

    if clan_stars > opp_stars:
        result_text = "Victory"
        color = 0x2ECC71
    elif clan_stars < opp_stars:
        result_text = "Defeat"
        color = 0xE74C3C
    else:
        result_text = "Tie"
        color = 0xF1C40F

    mvp_title, mvp_flavor = generate_war_mvp_title()

    embed = discord.Embed(
        title=f"⚔️ {mvp_title} • {clan_name} vs {opponent_name}",
        description=(
            f"**{result_text}**\n"
            f"{clan_name}: **{clan_stars}** ⭐ • **{clan_destruction:.1f}%**\n"
            f"{opponent_name}: **{opp_stars}** ⭐ • **{opp_destruction:.1f}%**\n\n"
            f"🔥 {mvp_flavor}"
        ),
        color=color,
    )
    mvp_lines = [
        f"🏆 **{mvp_display}**",
        f"⭐ {best_member['stars']} stars • 💥 {best_member['destruction']:.1f}% destruction",
        f"🎯 {best_member['triples']} triples • ⚔️ {best_member['attacks']} attacks",
    ]
    if mvp_total_reward > 0:
        mvp_lines.append(f"🪙 **Coins Awarded:** {mvp_total_reward}")
    embed.add_field(
        name="MVP",
        value="\n".join(mvp_lines),
        inline=False,
    )
    role_result = await rotate_war_mvp_role(
        guild=getattr(target_channel, "guild", None),
        role_id=WAR_MVP_ROLE_ID,
        mvp_discord_id=(mvp_reward or {}).get("discord_id"),
        state_file=CURRENT_WAR_MVP_FILE,
        war_id=get_war_id(war),
        player_name=best_member.get("name", "Unknown"),
        player_tag=best_member.get("tag", ""),
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        mvp_title=mvp_title,
    )
    presentation_result = await update_war_mvp_role_presentation(
        guild=getattr(target_channel, "guild", None),
        role_id=WAR_MVP_ROLE_ID,
        stars=best_member.get("stars", 0),
        destruction=best_member.get("destruction", 0),
        title=mvp_title,
        rename_role=False,
    )
    if role_result.get("ok"):
        role_note = "⚡ War MVP role assigned until the next War MVP is announced."
        if presentation_result.get("ok"):
            role_note += "\n🎨 Role color updated based on MVP performance."
        embed.add_field(
            name="Power Role",
            value=role_note,
            inline=False,
        )
    elif not role_result.get("skipped"):
        embed.add_field(
            name="Power Role",
            value=f"⚠️ Could not update War MVP role: {role_result.get('reason', 'unknown error')}",
            inline=False,
        )

    content = mvp_display if str(mvp_display).startswith("<@") else None
    await asyncio.wait_for(target_channel.send(content=content, embed=embed), timeout=10)

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

async def load_loot_drop():
    stored = await safe_load_json(LOOT_DROP_FILE)

    if not isinstance(stored, dict):
        stored = {}

    stored.setdefault("active", False)
    stored.setdefault("drop_id", None)
    stored.setdefault("channel_id", CLAN_CHAT_CHANNEL_ID)
    stored.setdefault("reward", 0)
    stored.setdefault("style", None)
    stored.setdefault("claimed_by", None)
    stored.setdefault("message_id", None)
    stored.setdefault("next_drop_at", None)
    return stored
    
async def schedule_next_loot_drop():
    drop = await load_loot_drop()

    delay_minutes = random.randint(LOOT_DROP_MIN_MINUTES, LOOT_DROP_MAX_MINUTES)
    next_drop_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

    drop["next_drop_at"] = next_drop_at.isoformat()
    await safe_save_json(LOOT_DROP_FILE, drop)

async def create_loot_drop():
    channel = bot.get_channel(CLAN_CHAT_CHANNEL_ID)
    if not channel:
        return False

    async with loot_drop_lock:
        current = await load_loot_drop()
        if current.get("active"):
            return False

        style = choose_weighted_loot_style()
        reward = random.choice(style["rewards"])
        spawn_text = random.choice(style["spawn_messages"]).format(reward=reward)
        drop_id = f"loot_{int(datetime.now(timezone.utc).timestamp())}_{random.randint(1000, 9999)}"

        reserved_data = {
            "active": True,
            "drop_id": drop_id,
            "channel_id": CLAN_CHAT_CHANNEL_ID,
            "reward": reward,
            "style": style["name"],
            "claimed_by": None,
            "message_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "next_drop_at": None,
        }

        await safe_save_json(LOOT_DROP_FILE, reserved_data)

        try:
            msg = await channel.send(spawn_text)
        except Exception:
            reserved_data["active"] = False
            await safe_save_json(LOOT_DROP_FILE, reserved_data)
            raise

        reserved_data["message_id"] = msg.id
        await safe_save_json(LOOT_DROP_FILE, reserved_data)
        return True

async def claim_loot_drop(message: discord.Message):
    if message.author.bot:
        return False

    if message.channel.id != CLAN_CHAT_CHANNEL_ID:
        return False

    if message.content.strip().lower() != "claim":
        return False

    async with loot_drop_lock:
        drop = await load_loot_drop()
        if not drop.get("active"):
            return False

        if drop.get("claimed_by"):
            return False

        linked_raw = await safe_load_json(LINKED_FILE)
        linked = normalize_linked_data(linked_raw)
        user_entries = linked.get(str(message.author.id), [])

        if not user_entries:
            await message.reply(
                "❌ You need to link your Clash account first with `/link` before claiming loot.",
                mention_author=False,
            )
            return True

        reward = int(drop.get("reward", 0))
        bonus_text = ""
        style_name = drop.get("style")
        player_name = user_entries[0].get("name", message.author.display_name)

        if await economy.consume_shop_item(str(message.author.id), "lucky_charm"):
            reward += SHOP_ITEMS["lucky_charm"]["bonus"]
            bonus_text = f"\n✨ Lucky Charm activated: +{SHOP_ITEMS['lucky_charm']['bonus']} coins"

        if await economy.consume_shop_item(str(message.author.id), "high_roller"):
            high_roller = SHOP_ITEMS["high_roller"]
            if random.random() < float(high_roller.get("bust_chance", 0.25)):
                reward = 0
                bonus_text += "\n🎲 High Roller busted: reward dropped to 0 coins."
            else:
                reward *= int(high_roller.get("multiplier", 2))
                bonus_text += f"\n🎲 High Roller hit: reward doubled to {reward} coins."

        await economy.award_loot_drop_coins(str(message.author.id), player_name, reward)

        drop["active"] = False
        drop["claimed_by"] = str(message.author.id)
        await safe_save_json(LOOT_DROP_FILE, drop)
        await schedule_next_loot_drop()

    style = next(
        (s for s in LOOT_DROP_STYLES if s["name"] == style_name),
        LOOT_DROP_STYLES[0],
    )
    win_text = random.choice(style["claim_messages"]).format(
        user=message.author.mention,
        reward=reward,
    )

    await message.reply(f"{win_text}{bonus_text}", mention_author=False)
    return True
    
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

def get_war_mvp_member(war):
    best_stats = get_war_mvp_stats(war)
    if not best_stats:
        return None
    for member in war.get("clan", {}).get("members", []):
        if member.get("name") == best_stats.get("name") and member.get("tag") == best_stats.get("tag"):
            return member
    return None

async def reward_war_coins(war):
    return await economy.reward_war_coins(war, get_war_id=get_war_id, get_war_mvp_member=get_war_mvp_member)

async def reward_clutch_coins(member_tag, member_name, attack_id, clutch_type=None):
    return await economy.reward_clutch_coins(member_tag, member_name, attack_id, clutch_type=clutch_type)

def get_clutch_reward_amount(clutch_type):
    return int(CLUTCH_REWARD_TIERS.get(str(clutch_type or ""), CLUTCH_COIN_REWARD))

async def post_final_war_summary(war, war_rewards=None):
    if war.get("state") != "warEnded":
        return

    summary_channel = bot.get_channel(WAR_SUMMARY_CHANNEL_ID)
    if not summary_channel:
        return

    summary_key = get_war_id(war)
    posted = await safe_load_json(WAR_SUMMARY_POSTS_FILE)
    if not isinstance(posted, dict):
        posted = {}
    if posted.get(summary_key):
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    clan_stars = clan.get("stars", 0)
    opp_stars = opponent.get("stars", 0)

    color = 0x2ECC71
    if clan_stars < opp_stars:
        color = 0xE74C3C
    elif clan_stars == opp_stars:
        color = 0xF1C40F

    buffer = await create_final_war_image(war)
    file = discord.File(fp=buffer, filename="final_war.png")
    embed = discord.Embed(
        title=f"War Summary • {clan.get('name', 'Our Clan')} vs {opponent.get('name', 'Opponent')}",
        color=color,
    )
    best_member = get_war_mvp_stats(war)
    if best_member:
        mvp_reward = war_rewards.get("mvp") if isinstance(war_rewards, dict) else None
        mvp_display = format_member_mention(
            (mvp_reward or {}).get("discord_id"),
            best_member.get("name", "Unknown"),
        )
        mvp_total_reward = int((mvp_reward or {}).get("total_reward", 0))
        description_lines = [
            f"🏆 **War MVP:** {mvp_display}",
            f"⭐ {best_member['stars']} stars • 💥 {best_member['destruction']:.1f}% destruction • 🎯 {best_member['triples']} triples",
        ]
        if mvp_total_reward > 0:
            description_lines.append(f"🪙 **MVP Coins Awarded:** {mvp_total_reward}")
        embed.description = "\n".join(description_lines)
    embed.set_image(url="attachment://final_war.png")

    mention_content = None
    if isinstance(war_rewards, dict):
        discord_id = ((war_rewards.get("mvp") or {}).get("discord_id"))
        if discord_id:
            mention_content = f"<@{discord_id}>"

    await asyncio.wait_for(summary_channel.send(content=mention_content, embed=embed, file=file), timeout=10)
    posted[summary_key] = {
        "clan_tag": clan.get("tag"),
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    await safe_save_json(WAR_SUMMARY_POSTS_FILE, posted)

# ---------------- HTTP SESSION MANAGEMENT ----------------

async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
    return session

async def close_session():
    global session
    if session and not session.closed:
        await session.close()
        session = None

# ---------------- Clash API ----------------

async def fetch_json(url, retries=3):
    sess = await get_session()

    for attempt in range(retries):
        try:
            async with sess.get(url, headers=HEADERS) as r:

                if r.status == 200:
                    return await r.json()

                elif r.status == 429:
                    print("Rate limited. Sleeping...")
                    await asyncio.sleep(5)

                else:
                    print(f"HTTP {r.status} for {url}")
                    return None

        except asyncio.TimeoutError:
            print(f"[Timeout] Attempt {attempt+1}/{retries}")

        except aiohttp.ClientError as e:
            print(f"[ClientError] {e}")

        await asyncio.sleep(2)  # small delay before retry

    print(f"[FAILED] Could not fetch {url}")
    return None

async def fetch_clan_data(clan_tag: str):
    encoded_tag = clan_tag.replace("#", "%23")

    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    cache_suffix = clan_tag.replace("#", "")

    war, members_json = await asyncio.gather(
        get_cached_or_fetch(f"war_{cache_suffix}", war_url, ttl=60),
        get_cached_or_fetch(f"members_{cache_suffix}", members_url, ttl=300),
    )

    if not members_json:
        print(f"⚠️ Member fetch failed for {clan_tag}")
        return war, []

    return war, members_json.get("items", [])


async def fetch_all_data():
    if not MAIN_CLAN_TAG:
        print("⚠️ No main clan tag configured")
        return None, None

    return await fetch_clan_data(MAIN_CLAN_TAG)

# ---------------- WAR PLAN ----------------

def build_war_plan_data(war, data):
    assignments = data.get("assignments", [])
    hit_order = data.get("hit_order", [])
    captain_calls = data.get("captain_calls", [])

    filtered_assignments = []
    for a in assignments:
        target = next(
            (
                t
                for t in war.get("opponent", {}).get("members", [])
                if t.get("mapPosition") == a["primary"]
            ),
            None,
        )
        if not target:
            continue

        best = target.get("bestOpponentAttack")
        if best and best.get("stars") == 3:
            continue

        filtered_assignments.append(a)

    target_map = defaultdict(list)
    for a in filtered_assignments:
        target_map[a["primary"]].append(a)

    plan_targets = []
    for target_num, attackers in sorted(target_map.items()):
        attackers_sorted = sorted(
            attackers,
            key=lambda x: (
                hit_order.index(x["player"]) if x["player"] in hit_order else 999
            ),
        )

        target_attackers = []
        for i, atk in enumerate(attackers_sorted):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "•"
            line = atk["player"]
            if atk.get("backup"):
                backups = ", ".join(f"#{b}" for b in atk["backup"])
                line += f" ↪ Backup: {backups}"

            target_attackers.append(
                {
                    "medal": medal,
                    "text": line,
                }
            )

        plan_targets.append(
            {
                "target": target_num,
                "attackers": target_attackers,
            }
        )

    return {
        "targets": plan_targets,
        "captain_calls": captain_calls,
    }

def render_war_plan_html(plan_data):
    targets = plan_data.get("targets", [])
    captain_calls = plan_data.get("captain_calls", [])

    target_cards = []
    for t in targets:
        attackers_html = "".join(
            f'<div class="plan-attacker"><span class="plan-medal">{a["medal"]}</span> <span>{a["text"]}</span></div>'
            for a in t["attackers"]
        )

        target_cards.append(
            f"""
        <div class="plan-card">
            <div class="plan-card-title">Target #{t["target"]}</div>
            {attackers_html}
        </div>
        """
        )

    calls_html = (
        "".join(f"<li>{call}</li>" for call in captain_calls)
        or "<li>No captain calls</li>"
    )

    if not target_cards:
        target_cards_html = '<div class="plan-empty">No suggestions available.</div>'
    else:
        target_cards_html = "".join(target_cards)

    return f"""
    <div class="war-plan-section">
        <div class="war-plan-title">War Plan</div>
        <div class="war-plan-layout">
            <div class="war-plan-grid">
                {target_cards_html}
            </div>
            <div class="captain-panel">
                <div class="captain-title">Captain Calls</div>
                <ul class="captain-list">
                    {calls_html}
                </ul>
            </div>
        </div>
    </div>
    """

# ---------------- BATTLE DAY UI ----------------

async def create_war_image(war, ai_data):
    def _read_template():
        with open(WAR_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    html = await asyncio.to_thread(_read_template)

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})
    war_state = war.get("state", "")

    clan_badge = clan.get("badgeUrls", {}).get("large", "")
    opponent_badge = opponent.get("badgeUrls", {}).get("large", "")

    clan_stars = clan.get("stars", 0) or 0
    opponent_stars = opponent.get("stars", 0) or 0

    clan_destruction = float(clan.get("destructionPercentage", 0) or 0)
    opponent_destruction = float(opponent.get("destructionPercentage", 0) or 0)

    clan_attacks = clan.get("attacks", 0) or 0
    opponent_attacks = opponent.get("attacks", 0) or 0

    team_size = war.get("teamSize", 0) or 0
    attacks_per_member = war.get("attacksPerMember", 2) or 2
    max_attacks = team_size * attacks_per_member

    total_stars = clan_stars + opponent_stars
    if total_stars > 0:
        clan_stars_pct = int((clan_stars / total_stars) * 100)
        opponent_stars_pct = 100 - clan_stars_pct
    else:
        clan_stars_pct = 50
        opponent_stars_pct = 50

    clan_destruction_pct = max(0, min(100, int(round(clan_destruction))))
    opponent_destruction_pct = max(0, min(100, int(round(opponent_destruction))))

    clan_attacks_pct = int((clan_attacks / max_attacks) * 100) if max_attacks else 0
    opponent_attacks_pct = (
        int((opponent_attacks / max_attacks) * 100) if max_attacks else 0
    )

    def attack_star_buckets(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        return {
            3: sum(1 for a in attacks if a.get("stars") == 3),
            2: sum(1 for a in attacks if a.get("stars") == 2),
            1: sum(1 for a in attacks if a.get("stars") == 1),
            0: sum(1 for a in attacks if a.get("stars") == 0),
        }

    clan_buckets = attack_star_buckets(clan)
    opp_buckets = attack_star_buckets(opponent)

    clan_avg_stars = round(clan_stars / clan_attacks, 2) if clan_attacks else 0
    opp_avg_stars = (
        round(opponent_stars / opponent_attacks, 2) if opponent_attacks else 0
    )

    def average_attack_destruction(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        if not attacks:
            return 0
        total_destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        return round(total_destruction / len(attacks), 2)

    clan_avg_dest = average_attack_destruction(clan)
    opp_avg_dest = average_attack_destruction(opponent)

    end_time = war.get("endTime")
    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(
            tzinfo=timezone.utc
        )
        now = datetime.now(timezone.utc)
        diff = end_dt - now
        total_seconds = int(diff.total_seconds())

        if total_seconds <= 0:
            time_remaining = "Ended"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            time_remaining = f"{hours}h {minutes:02d}m"
    else:
        time_remaining = "N/A"

    def calculate_actual_mvp(clan_data):
        best_name = None
        best_score = -1

        for member in clan_data.get("members", []):
            attacks = member.get("attacks", [])
            if not attacks:
                continue

            stars = sum(a.get("stars", 0) for a in attacks)
            destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
            score = stars * 100 + destruction

            if score > best_score:
                best_score = score
                best_name = member.get("name")

        return best_name

    if war_state == "warEnded":
        mvp = calculate_actual_mvp(clan) or "TBD"
        mvp_label = "War MVP"
        war_plan_html = ""
        war_insights_html = """
        <div class="war-insights-section">
            <div class="war-insights-title">War Insights</div>
            <div class="war-insights-grid">
                <div class="war-insight-card">
                    <div class="war-insight-label">Phase</div>
                    <div class="war-insight-value">Ended</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Strategy</div>
                    <div class="war-insight-value">Ended</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Win Chance</div>
                    <div class="war-insight-value">—</div>
                </div>
            </div>
        </div>
        """
    else:
        mvp = ai_data.get("mvp") or "—"
        mvp_label = "Predicted MVP"
        plan_data = build_war_plan_data(war, ai_data)
        war_plan_html = render_war_plan_html(plan_data)

        phase = str(ai_data.get("phase", "N/A")).title()
        strategy = str(ai_data.get("strategy", "N/A")).title()
        win_chance = ai_data.get("win_chance")
        win_chance_text = (
            f"{win_chance:.1f}%" if isinstance(win_chance, (int, float)) else "—"
        )

        war_insights_html = f"""
        <div class="war-insights-section">
            <div class="war-insights-title">War Insights</div>
            <div class="war-insights-grid">
                <div class="war-insight-card">
                    <div class="war-insight-label">Phase</div>
                    <div class="war-insight-value">{phase}</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Strategy</div>
                    <div class="war-insight-value">{strategy}</div>
                </div>
                <div class="war-insight-card">
                    <div class="war-insight-label">Win Chance</div>
                    <div class="war-insight-value">{win_chance_text}</div>
                </div>
            </div>
        </div>
        """

    replacements = {
        "{{CLAN_BADGE}}": clan_badge,
        "{{OPPONENT_BADGE}}": opponent_badge,
        "{{TIME_REMAINING}}": time_remaining,
        "{{CLAN_STARS}}": str(clan_stars),
        "{{OPPONENT_STARS}}": str(opponent_stars),
        "{{CLAN_STARS_PCT}}": str(clan_stars_pct),
        "{{OPPONENT_STARS_PCT}}": str(opponent_stars_pct),
        "{{CLAN_DESTRUCTION}}": f"{clan_destruction:.2f}",
        "{{OPPONENT_DESTRUCTION}}": f"{opponent_destruction:.2f}",
        "{{CLAN_DESTRUCTION_PCT}}": str(clan_destruction_pct),
        "{{OPPONENT_DESTRUCTION_PCT}}": str(opponent_destruction_pct),
        "{{CLAN_ATTACKS}}": f"{clan_attacks}/{max_attacks}",
        "{{OPPONENT_ATTACKS}}": f"{opponent_attacks}/{max_attacks}",
        "{{CLAN_ATTACKS_PCT}}": str(clan_attacks_pct),
        "{{OPPONENT_ATTACKS_PCT}}": str(opponent_attacks_pct),
        "{{CLAN_3STARS}}": str(clan_buckets[3]),
        "{{OPP_3STARS}}": str(opp_buckets[3]),
        "{{CLAN_2STARS}}": str(clan_buckets[2]),
        "{{OPP_2STARS}}": str(opp_buckets[2]),
        "{{CLAN_1STARS}}": str(clan_buckets[1]),
        "{{OPP_1STARS}}": str(opp_buckets[1]),
        "{{CLAN_0STARS}}": str(clan_buckets[0]),
        "{{OPP_0STARS}}": str(opp_buckets[0]),
        "{{CLAN_AVG_STARS}}": f"{clan_avg_stars:.2f}",
        "{{OPP_AVG_STARS}}": f"{opp_avg_stars:.2f}",
        "{{CLAN_AVG_DEST}}": f"{clan_avg_dest:.2f}",
        "{{OPP_AVG_DEST}}": f"{opp_avg_dest:.2f}",
        "{{MVP}}": str(mvp),
        "{{MVP_LABEL}}": str(mvp_label),
        "{{CLAN_NAME}}": clan.get("name", "Clan"),
        "{{OPPONENT_NAME}}": opponent.get("name", "Opponent"),
        "{{WAR_INSIGHTS_HTML}}": war_insights_html,
        "{{WAR_PLAN_HTML}}": war_plan_html,
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1000, "height": 1150})
        page.set_default_timeout(10000)

        await page.set_content(html, wait_until="domcontentloaded")
        await page.wait_for_timeout(1200)

        await page.screenshot(path="/app/war.png", full_page=True)
        await browser.close()

    return open("/app/war.png", "rb")

# ---------------- WAR SUMMARY IMAGE ----------------

async def create_final_war_image(war):
    def _read_template():
        with open(FINAL_WAR_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    html = await asyncio.to_thread(_read_template)

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    clan_name = clan.get("name", "Clan")
    opponent_name = opponent.get("name", "Opponent")

    clan_badge = clan.get("badgeUrls", {}).get("large", "")
    opponent_badge = opponent.get("badgeUrls", {}).get("large", "")

    clan_stars = clan.get("stars", 0) or 0
    opp_stars = opponent.get("stars", 0) or 0

    clan_destruction = float(clan.get("destructionPercentage", 0) or 0)
    opp_destruction = float(opponent.get("destructionPercentage", 0) or 0)

    clan_attacks = clan.get("attacks", 0) or 0
    opp_attacks = opponent.get("attacks", 0) or 0

    team_size = war.get("teamSize", 0) or 0
    attacks_per_member = war.get("attacksPerMember", 2) or 2
    max_attacks = team_size * attacks_per_member

    def attack_star_buckets(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        return {
            3: sum(1 for a in attacks if a.get("stars") == 3),
            2: sum(1 for a in attacks if a.get("stars") == 2),
            1: sum(1 for a in attacks if a.get("stars") == 1),
            0: sum(1 for a in attacks if a.get("stars") == 0),
        }

    clan_buckets = attack_star_buckets(clan)
    opp_buckets = attack_star_buckets(opponent)

    def average_attack_destruction(side):
        attacks = [a for m in side.get("members", []) for a in m.get("attacks", [])]
        if not attacks:
            return 0
        total_destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        return round(total_destruction / len(attacks), 2)

    clan_avg_stars = round(clan_stars / clan_attacks, 2) if clan_attacks else 0
    opp_avg_stars = round(opp_stars / opp_attacks, 2) if opp_attacks else 0
    clan_avg_dest = average_attack_destruction(clan)
    opp_avg_dest = average_attack_destruction(opponent)

    result = "Victory"
    result_color = "#2ECC71"
    if clan_stars < opp_stars:
        result = "Defeat"
        result_color = "#E74C3C"
    elif clan_stars == opp_stars:
        result = "Draw"
        result_color = "#F1C40F"

    def calculate_actual_mvp(clan_data):
        best_name = None
        best_score = -1

        for member in clan_data.get("members", []):
            attacks = member.get("attacks", [])
            if not attacks:
                continue

            stars = sum(a.get("stars", 0) for a in attacks)
            destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
            score = stars * 100 + destruction

            if score > best_score:
                best_score = score
                best_name = member.get("name")

        return best_name or "—"

    mvp = calculate_actual_mvp(clan)

    replacements = {
        "{{CLAN_NAME}}": clan_name,
        "{{OPPONENT_NAME}}": opponent_name,
        "{{CLAN_BADGE}}": clan_badge,
        "{{OPPONENT_BADGE}}": opponent_badge,
        "{{RESULT}}": result,
        "{{RESULT_COLOR}}": result_color,
        "{{CLAN_STARS}}": str(clan_stars),
        "{{OPPONENT_STARS}}": str(opp_stars),
        "{{CLAN_DESTRUCTION}}": f"{clan_destruction:.2f}",
        "{{OPPONENT_DESTRUCTION}}": f"{opp_destruction:.2f}",
        "{{CLAN_ATTACKS}}": f"{clan_attacks}/{max_attacks}",
        "{{OPPONENT_ATTACKS}}": f"{opp_attacks}/{max_attacks}",
        "{{CLAN_3STARS}}": str(clan_buckets[3]),
        "{{OPP_3STARS}}": str(opp_buckets[3]),
        "{{CLAN_2STARS}}": str(clan_buckets[2]),
        "{{OPP_2STARS}}": str(opp_buckets[2]),
        "{{CLAN_1STARS}}": str(clan_buckets[1]),
        "{{OPP_1STARS}}": str(opp_buckets[1]),
        "{{CLAN_0STARS}}": str(clan_buckets[0]),
        "{{OPP_0STARS}}": str(opp_buckets[0]),
        "{{CLAN_AVG_STARS}}": f"{clan_avg_stars:.2f}",
        "{{OPP_AVG_STARS}}": f"{opp_avg_stars:.2f}",
        "{{CLAN_AVG_DEST}}": f"{clan_avg_dest:.2f}",
        "{{OPP_AVG_DEST}}": f"{opp_avg_dest:.2f}",
        "{{MVP}}": mvp,
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1000, "height": 900})
        page.set_default_timeout(10000)

        await page.set_content(html, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        await page.screenshot(path=FINAL_WAR_IMAGE_PATH, full_page=True)
        await browser.close()

    return open(FINAL_WAR_IMAGE_PATH, "rb")

# ---------------- NEW DONATION LEADBOARD ----------------

async def create_donation_image(leaderboard):
    def _read_template():
        with open(DONATION_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()

    html = await asyncio.to_thread(_read_template)

    if not leaderboard:
        rows_html = '<div class="donation-empty">No donation data available.</div>'
        total_donations = 0
        total_received = 0
    else:
        max_don = max([m["donations"] for m in leaderboard] + [1])
        total_donations = sum(m["donations"] for m in leaderboard)
        total_received = sum(m["received"] for m in leaderboard)

        rows = []
        for i, m in enumerate(leaderboard[:10]):
            if i == 0:
                medal = "🥇"
                display_name = f'👑 {m["name"]}'
            elif i == 1:
                medal = "🥈"
                display_name = m["name"]
            elif i == 2:
                medal = "🥉"
                display_name = m["name"]
            else:
                medal = f"#{i+1}"
                display_name = m["name"]

            width_pct = int((m["donations"] / max_don) * 100) if max_don else 0
            rows.append(
                f"""
                <div class="donation-row">
                    <div class="donation-rank">{medal}</div>
                    <div class="donation-main">
                        <div class="donation-name">{display_name}</div>
                        <div class="donation-bar">
                            <div class="donation-fill" style="width: {width_pct}%"></div>
                        </div>
                    </div>
                    <div class="donation-stats">
                        <div><strong>{m["donations"]}</strong> donated</div>
                        <div>{m["received"]} received</div>
                    </div>
                </div>
                """
            )

        rows_html = "".join(rows)

    replacements = {
        "{{ROWS_HTML}}": rows_html,
        "{{TOTAL_DONATIONS}}": str(total_donations),
        "{{TOTAL_RECEIVED}}": str(total_received),
    }

    for key, value in replacements.items():
        html = html.replace(key, value)

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1000, "height": 1150})
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(500)
        await page.screenshot(path=DONATION_IMAGE_PATH, full_page=True)
        await browser.close()

    return open(DONATION_IMAGE_PATH, "rb")

# ---------------- NEW DONATION LEADBOARD ----------------

async def update_donation_leaderboard(members, channel: discord.TextChannel):
    if not channel:
        return

    season_key = datetime.now(timezone.utc).strftime("%Y-%m")

    def _update_donations(stored):
        if not isinstance(stored, dict):
            stored = {}

        previous_season = stored.get("season")
        if previous_season != season_key:
            print(
                f"[DONATIONS] New month detected. Resetting donations "
                f"from {previous_season} to {season_key}"
            )

        # Rebuild from CURRENT clan members only so stale / feeder / departed
        # accounts do not remain eligible for the monthly donation MVP.
        current_players = {}
        for m in members:
            tag = m.get("tag")
            if not tag:
                continue

            current_players[tag] = {
                "tag": tag,
                "name": m.get("name", "")[:12],
                "donations": int(m.get("donations", 0) or 0),
                "received": int(m.get("donationsReceived", 0) or 0),
            }

        return {
            "season": season_key,
            "players": current_players,
        }

    stored = await update_json_file(DONATION_FILE, _update_donations)
    leaderboard = sorted(
        stored.get("players", {}).values(),
        key=lambda x: x["donations"],
        reverse=True
    )
    
    monthly_mvp_name, monthly_mvp_data = get_current_monthly_mvp(stored)

    buffer = await create_donation_image(leaderboard)
    file = discord.File(fp=buffer, filename="donations.png")

    embed = discord.Embed(
        title=f"Monthly Donations - {season_key}",
        color=0x2C2F33
    )

    if monthly_mvp_name and monthly_mvp_data:
        donated = int(monthly_mvp_data.get("donations", 0) or 0)
        received = int(monthly_mvp_data.get("received", 0) or 0)
        ratio_text = "∞" if received == 0 and donated > 0 else (
            f"{(donated / received):.2f}x" if received > 0 else "0.00x"
        )
        embed.description = (
            f"🏆 **Top Donor This Month:** {monthly_mvp_name}\n"
            f"📦 {donated} donated"
            f" • 📥 {received} received"
            f" • 📊 {ratio_text} ratio"
        )

    embed.set_image(url="attachment://donations.png")

    mid = await get_saved_message(LEADERBOARD_MESSAGE_FILE)
    msg = None
    if mid:
        try:
            msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            msg = None

    if msg:
        try:
            await msg.edit(embeds=[embed], attachments=[file])
        except discord.HTTPException:
            pass
    else:
        new_msg = await asyncio.wait_for(
            channel.send(embed=embed, file=file), timeout=10
        )
        await save_message(LEADERBOARD_MESSAGE_FILE, new_msg.id)

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
        "suggestions": suggestions[:10],
        "assignments": assignments,
        "hit_order": hit_order,
        "phase": phase,
        "strategy": strategy,
        "captain_calls": captain_lines,
        "win_chance": round(win_chance, 1),
        "mvp": predicted_mvp,
    }

async def process_war_updates(war, members, clan_tag: str, is_main_clan: bool = False):
    """Main war update dispatcher."""

    # Only the main clan should update the existing war dashboard/message files
    if is_main_clan:
        await update_war_dashboard(war, members)

    # Both clans can still generate clutch moments
    await process_clutch_attacks(war)

    # Both clans should earn war-end rewards and get a war summary/MVP post
    if war.get("state") == "warEnded":
        war_rewards = await reward_war_coins(war)
        await update_monthly_mvp_from_war(war)
        await post_final_war_summary(war, war_rewards=war_rewards)
    
# ---------------- UPDATE LOOP ----------------

@tasks.loop(minutes=2)
async def update_loop():
    await asyncio.sleep(1)

    try:
        for clan_tag in CLAN_TAGS:
            if not clan_tag:
                continue

            is_main_clan = clan_tag == MAIN_CLAN_TAG

            war, members = await fetch_clan_data(clan_tag)

            # Keep the existing donation leaderboard tied to the main clan only
            if is_main_clan:
                stats_channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
                if stats_channel and members:
                    await update_donation_leaderboard(members, stats_channel)

            # Process war logic for both clans
            if war:
                await process_war_updates(war, members, clan_tag, is_main_clan=is_main_clan)

    except Exception as e:
        print(f"[UPDATE LOOP ERROR] {e}")
        traceback.print_exc() 
        
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

async def update_war_dashboard(war, full_members):
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    ended_data = await safe_load_json(WAR_END_FILE)
    state = war.get("state", "N/A")
    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    if state != "warEnded" and ended_data.get("posted"):
        await safe_save_json(WAR_END_FILE, {"posted": False})
        await reset_war_pings()
        ended_data = {"posted": False}

    mid = await get_saved_message(WAR_MESSAGE_FILE)
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
            await war_msg.edit(embeds=[embed], attachments=[file])
        except discord.HTTPException:
            pass
    else:
        new_msg = await asyncio.wait_for(
            channel.send(embed=embed, file=file), timeout=10
        )
        await save_message(WAR_MESSAGE_FILE, new_msg.id)

# ---------------- FINAL WAR IMAGE (RUN ONCE) ----------------
    if state == "warEnded" and not ended_data.get("posted"):
        await safe_save_json(WAR_END_FILE, {"posted": True})

# ---------------- CHECK WAR PINGS ----------------

    await check_war_pings(war)
    await check_unlinked_players(war)

# ---------------- WAR PINGS ----------------

async def ping_users_for_interval(interval, members, attacks_per_member):
    linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    current_pings = await safe_load_json(WAR_PINGS_FILE)
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

        await update_json_file(WAR_PINGS_FILE, _update_pings)


async def check_war_pings(war):
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
        await ping_users_for_interval("start", members, attacks_per_member)

    if timedelta(hours=11, minutes=50) <= time_left <= timedelta(hours=12, minutes=10):
        await ping_users_for_interval("12h", members, attacks_per_member)

    if timedelta(minutes=50) <= time_left <= timedelta(hours=1, minutes=10):
        await ping_users_for_interval("1h", members, attacks_per_member)

    if timedelta(seconds=0) <= time_left <= timedelta(minutes=10):
        await ping_users_for_interval("end", members, attacks_per_member)

async def check_unlinked_players(war):
    members = war.get("clan", {}).get("members", [])
    linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
    warned = await safe_load_json(UNLINKED_WARN_FILE)

    channel = bot.get_channel(WAR_CHANNEL_ID)
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
            + "\n\nPlease run `/link` in **#ama-clash-link** to enable war reminders."
        )
        await asyncio.wait_for(channel.send(msg, delete_after=3600), timeout=10)

    if tags_to_mark:

        def _update_warned(data):
            for tag in tags_to_mark:
                data[tag] = True
            return data

        await update_json_file(UNLINKED_WARN_FILE, _update_warned)

# ---------------- LINK AUDIT COMMAND ----------------


from types import SimpleNamespace

command_context = SimpleNamespace(**{
    name: globals()[name]
    for name in [
        "LEADER_ROLE_ID", "CO_LEADER_ROLE_ID", "CLAN_CHAT_CHANNEL_ID",
        "LOOT_DROP_FILE", "SHOP_ITEMS", "LOOT_DROP_STYLES", "LINKED_FILE", "COIN_LEADERBOARD_IMAGE_PATH",
        "CLAN_TAGS", "MAIN_CLAN_TAG", "TAG_REGEX",
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
