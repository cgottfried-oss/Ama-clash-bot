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
from types import SimpleNamespace
from clan_bot.renderers.html_renderer import render_html_to_png_buffer, close_playwright_renderer
from clan_bot.renderers.war_renderer import render_war_template_to_png, render_final_war_template_to_png
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from commands import register_all_commands
from shared.storage import safe_load_json, safe_save_json, update_json_file
from clan_bot.linked_accounts import normalize_tag, normalize_user_linked_data as normalize_linked_data, build_tag_to_discord_map
from clan_bot.war.reward_config import (
    STAR_COIN_REWARD,
    WAR_MVP_BONUS,
    CLUTCH_COIN_REWARD,
    CLUTCH_REWARD_TIERS,
)
from clan_bot.war_mvp import (
    generate_war_mvp_title,
    rotate_war_mvp_role,
    update_war_mvp_role_presentation,
)
from clan_bot.runtime import (
    create_clash_client,
    create_economy_manager,
    create_war_runtime_context,
)
import discord
from discord.ext import tasks, commands
from discord import app_commands
from clan_bot.tasks.update_loop import run_update_cycle
from clan_bot.features.donations import update_donation_leaderboard as donation_update
from clan_bot.war.clutch_posts import post_clutch_moment, post_clutch_summary
from clan_bot.snapshot_progress.snapshot_commands import register_clan_snapshot_command
from clan_bot.war import clutch as war_clutch
from clan_bot.war import mvp as war_mvp
from clan_bot.war import summaries as war_summaries
from clan_bot.war import planning as war_planning
from clan_bot.war import images as war_images
from clan_bot.war import rewards as war_rewards
from clan_bot.snapshot_progress.progress_commands import register_current_progress_command
from clash_mmo.services.economy import EconomyManager
import clash_mmo.services.loot_drops as loot_drops
from clash_mmo.config.economy_config import SHOP_ITEMS, LOOT_DROP_STYLES

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
CLASH_MMO_CHANNEL_ID = int(os.getenv("CLASH_MMO_CHANNEL_ID", CLAN_CHAT_CHANNEL_ID))
MMO_OWNER_ID = int(os.getenv("MMO_OWNER_ID", "0") or 0)
WAR_MVP_ROLE_ID = int(os.getenv("WAR_MVP_ROLE_ID", "0") or 0)

# ---------------- PATHS ----------------

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
ASSETS_DIR = "/app/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)
TEMPLATES_DIR = "/app/clan_bot/templates"

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
            for attack in member.get("attacks", []) or []:
                attack_id = build_attack_id(member_tag, attack)
                current_attack_ids.add(attack_id)

                if attack_id in new_log:
                    continue

                if is_clutch_attack(attack, war, attacker_tag=member_tag):
                    new_clutch_hits.append((member, attack, attack_id))

    if stored_signature == war_signature and initialized:
        for member, attack, attack_id in new_clutch_hits:
            attacker_name = member.get("name", "Unknown")
            stars = attack.get("stars", 0)
            destruction = attack.get("destructionPercentage", 0)

            await economy.reward_clutch_coins(str(member.get("tag", "")), attacker_name)
            await post_clutch_moment(
                bot,
                WAR_CHANNEL_ID,
                attacker_name,
                stars,
                destruction,
                attack,
            )

    new_log.update(current_attack_ids)
    await safe_save_json(log_file, sorted(new_log))

    state["war_signature"] = war_signature
    state["initialized"] = True
    await safe_save_json(state_file, state)

async def war_mvp_month_key():

    return war_mvp.war_mvp_month_key()

async def load_monthly_mvp():

    return await war_mvp.load_monthly_mvp(safe_load_json, MONTHLY_MVP_FILE)

async def save_monthly_mvp(data):

    await war_mvp.save_monthly_mvp(safe_save_json, MONTHLY_MVP_FILE, data)

async def load_current_war_mvp():

    return await war_mvp.load_current_war_mvp(safe_load_json, CURRENT_WAR_MVP_FILE)

async def save_current_war_mvp(data):

    await war_mvp.save_current_war_mvp(safe_save_json, CURRENT_WAR_MVP_FILE, data)

async def award_war_mvp(player_tag, player_name, points):

    await war_mvp.award_war_mvp(

        bot,

        player_tag,

        player_name,

        points,

        safe_load_json=safe_load_json,

        safe_save_json=safe_save_json,

        monthly_mvp_file=MONTHLY_MVP_FILE,

        current_war_mvp_file=CURRENT_WAR_MVP_FILE,

        war_mvp_bonus=WAR_MVP_BONUS,

        war_mvp_role_id=WAR_MVP_ROLE_ID,

        war_channel_id=WAR_CHANNEL_ID,

        generate_war_mvp_title=generate_war_mvp_title,

        rotate_war_mvp_role=rotate_war_mvp_role,

        update_war_mvp_role_presentation=update_war_mvp_role_presentation,

        economy=economy,

    )

async def post_clutch_summary_command(interaction):

    await post_clutch_summary(bot, interaction, PERFORMANCE_FILE)

async def clan_request(path, params=None):
    global session

    if session is None or session.closed:
        session = aiohttp.ClientSession()

    url = f"https://api.clashofclans.com/v1{path}"

    try:
        async with session.get(url, headers=HEADERS, params=params, timeout=20) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Clash API error {resp.status}: {text[:300]}")
            return await resp.json()
    except Exception as e:
        print("API ERROR:", e)
        return None

async def get_current_war(clan_tag: str | None = None):
    tag = normalize_tag(clan_tag or MAIN_CLAN_TAG or (CLAN_TAGS[0] if CLAN_TAGS else ""))
    if not tag:
        return None
    encoded = tag.replace("#", "%23")
    return await clan_request(f"/clans/{encoded}/currentwar")

async def get_war_league_group(clan_tag: str | None = None):
    tag = normalize_tag(clan_tag or MAIN_CLAN_TAG or (CLAN_TAGS[0] if CLAN_TAGS else ""))
    if not tag:
        return None
    encoded = tag.replace("#", "%23")
    return await clan_request(f"/clans/{encoded}/currentwar/leaguegroup")

async def get_cwl_round_war(war_tag):
    encoded = normalize_tag(war_tag).replace("#", "%23")
    return await clan_request(f"/clanwarleagues/wars/{encoded}")

async def get_clan_members(clan_tag: str | None = None):
    tag = normalize_tag(clan_tag or MAIN_CLAN_TAG or (CLAN_TAGS[0] if CLAN_TAGS else ""))
    if not tag:
        return []
    encoded = tag.replace("#", "%23")
    data = await clan_request(f"/clans/{encoded}/members")
    return data.get("items", []) if data else []

async def get_clan_info(clan_tag: str | None = None):
    tag = normalize_tag(clan_tag or MAIN_CLAN_TAG or (CLAN_TAGS[0] if CLAN_TAGS else ""))
    if not tag:
        return None
    encoded = tag.replace("#", "%23")
    return await clan_request(f"/clans/{encoded}")

async def close_session():
    global session
    if session and not session.closed:
        await session.close()
        session = None

# ---------------- HELPERS ----------------

def war_state_label(state):
    return war_summaries.war_state_label(state)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def destruction_pct(side):
    return war_summaries.destruction_pct(side)


def stars(side):
    return war_summaries.stars(side)


def attacks_used(side):
    return war_summaries.attacks_used(side)


def attacks_total(side):
    return war_summaries.attacks_total(side)


def clan_name(side):
    return war_summaries.clan_name(side)


def sort_members_by_map(members):
    return war_summaries.sort_members_by_map(members)


def format_attack_line(attack, members_by_tag):
    return war_summaries.format_attack_line(attack, members_by_tag)


def score_attack_quality(attack, attacker_th=None, defender_th=None):
    return war_rewards.score_attack_quality(
        attack,
        attacker_th=attacker_th,
        defender_th=defender_th,
    )


def evaluate_attack(member, attack, war, attacker_tag=None):
    return war_rewards.evaluate_attack(
        member,
        attack,
        war,
        attacker_tag=attacker_tag,
        get_attacker_townhall_level=get_attacker_townhall_level,
        get_defender_townhall_level=get_defender_townhall_level,
    )


def build_reward_embed(title, description, rows, color=discord.Color.gold()):
    return war_rewards.build_reward_embed(
        title,
        description,
        rows,
        color=color,
        discord_module=discord,
    )

async def apply_war_rewards(war):
    return await war_rewards.apply_war_rewards(
        war,
        performance_file=PERFORMANCE_FILE,
        safe_load_json=safe_load_json,
        safe_save_json=safe_save_json,
        normalize_tag=normalize_tag,
        evaluate_attack=evaluate_attack,
        economy=economy,
        award_war_mvp=award_war_mvp,
        star_coin_reward=STAR_COIN_REWARD,
        clutch_coin_reward=CLUTCH_COIN_REWARD,
        clutch_reward_tiers=CLUTCH_REWARD_TIERS,
    )

async def build_war_embed(war):
    return await war_summaries.build_war_embed(
        war,
        discord_module=discord,
        war_state_label=war_state_label,
        stars=stars,
        destruction_pct=destruction_pct,
        attacks_used=attacks_used,
        attacks_total=attacks_total,
        clan_name=clan_name,
        sort_members_by_map=sort_members_by_map,
        format_attack_line=format_attack_line,
    )

async def build_cwl_embed():
    group = await get_war_league_group()
    if not group:
        return None

    embeds = []
    clans = {clan.get("tag"): clan.get("name", "Unknown") for clan in group.get("clans", [])}
    rounds = group.get("rounds", [])

    embed = discord.Embed(title="🏆 CWL Overview", color=discord.Color.purple())
    embed.add_field(name="State", value=group.get("state", "Unknown"), inline=True)
    embed.add_field(name="Season", value=group.get("season", "Unknown"), inline=True)

    for idx, rnd in enumerate(rounds, start=1):
        war_tags = rnd.get("warTags", [])
        lines = []
        for tag in war_tags[:4]:
            if tag == "#0":
                continue
            war = await get_cwl_round_war(tag)
            if not war:
                continue
            clan = war.get("clan", {})
            opp = war.get("opponent", {})
            lines.append(
                f"{clan.get('name', 'Clan')} {stars(clan)}⭐ vs "
                f"{opp.get('name', 'Enemy')} {stars(opp)}⭐"
            )
        if lines:
            embed.add_field(
                name=f"Round {idx}",
                value="\n".join(lines)[:1024],
                inline=False,
            )

    embeds.append(embed)
    return embeds

async def post_current_war_update():
    for clan_tag in CLAN_TAGS:
        war = await get_current_war(clan_tag)
        if not war or war.get("state") == "notInWar":
            continue

        channel_id = war_channel_id_for_clan(clan_tag)
        channel = bot.get_channel(channel_id)
        if not channel:
            continue

        embed = await build_war_embed(war)
        if not embed:
            continue

        message_file = scoped_state_file(WAR_MESSAGE_FILE, clan_tag)
        msg_id = await safe_load_json(message_file)
        if isinstance(msg_id, dict):
            msg_id = msg_id.get("message_id")

        try:
            if msg_id:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                await safe_save_json(message_file, {"message_id": msg.id})
        except Exception as e:
            print("War update message error:", e)
            try:
                msg = await channel.send(embed=embed)
                await safe_save_json(message_file, {"message_id": msg.id})
            except Exception:
                pass

        await process_clutch_attacks(war)

async def build_donation_embed():
    linked = await safe_load_json(LINKED_FILE)
    if not isinstance(linked, dict):
        linked = {}
    tag_map = build_tag_to_discord_map(linked)

    totals = defaultdict(lambda: {"donations": 0, "received": 0, "names": set()})

    for clan_tag in CLAN_TAGS:
        members = await get_clan_members(clan_tag)
        for m in members:
            tag = normalize_tag(m.get("tag"))
            if not tag:
                continue
            discord_id = tag_map.get(tag, tag)
            entry = totals[discord_id]
            entry["donations"] += safe_int(m.get("donations"))
            entry["received"] += safe_int(m.get("donationsReceived"))
            entry["names"].add(m.get("name", "Unknown"))

    sorted_rows = sorted(totals.items(), key=lambda kv: kv[1]["donations"], reverse=True)

    lines = []
    for idx, (discord_id, data) in enumerate(sorted_rows[:10], start=1):
        label = f"<@{discord_id}>" if str(discord_id).isdigit() else ", ".join(sorted(data["names"]))
        lines.append(
            f"**#{idx}** {label} — **{data['donations']:,}** donated / {data['received']:,} received"
        )

    embed = discord.Embed(title="📦 Donation Leaderboard", color=discord.Color.green())
    embed.description = "\n".join(lines) if lines else "No donation data yet."
    return embed, sorted_rows

async def post_donation_update():
    channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
    if not channel:
        return

    try:
        embed, rows = await build_donation_embed()
        await donation_update(
            bot,
            CLAN_STATS_CHANNEL_ID,
            DONATION_TEMPLATE_PATH,
            DONATION_IMAGE_PATH,
            LEADERBOARD_MESSAGE_FILE,
            render_html_to_png_buffer,
            safe_load_json,
            safe_save_json,
            get_clan_members,
            LINKED_FILE,
        )
    except Exception as e:
        print("Donation update error:", e)
        traceback.print_exc()

async def check_war_end():
    for clan_tag in CLAN_TAGS:
        war = await get_current_war(clan_tag)
        if not war or war.get("state") == "notInWar":
            continue

        end_file = scoped_state_file(WAR_END_FILE, clan_tag)
        end_data = await safe_load_json(end_file)
        if not isinstance(end_data, dict):
            end_data = {}

        signature = get_war_signature(war)
        if war.get("state") == "warEnded" and end_data.get("last_signature") != signature:
            rewards = await apply_war_rewards(war)

            channel_id = war_channel_id_for_clan(clan_tag)
            channel = bot.get_channel(channel_id)
            if channel and rewards:
                rows = []
                for r in rewards[:10]:
                    rows.append(
                        f"**{r.get('name','Unknown')}** — {r.get('stars',0)}⭐ "
                        f"{r.get('destruction',0)}% → +{r.get('coins',0)} coins"
                    )
                embed = build_reward_embed(
                    "🏁 War Rewards Paid",
                    f"{clan_name(war.get('clan', {}))} vs {clan_name(war.get('opponent', {}))}",
                    rows,
                    color=discord.Color.gold(),
                )
                await channel.send(embed=embed)

            end_data["last_signature"] = signature
            await safe_save_json(end_file, end_data)

async def run_all_updates():
    try:
        await post_current_war_update()
        await post_donation_update()
    except Exception:
        traceback.print_exc()

# ---------------- BACKGROUND TASK ----------------

@tasks.loop(minutes=10)
async def update_loop():
    await run_update_cycle(
        bot,
        get_current_war=get_current_war,
        get_war_league_group=get_war_league_group,
        get_cwl_round_war=get_cwl_round_war,
        get_clan_members=get_clan_members,
        get_clan_info=get_clan_info,
        build_war_embed=build_war_embed,
        post_current_war_update=post_current_war_update,
        post_donation_update=post_donation_update,
        check_war_end=check_war_end,
        data_dir=DATA_DIR,
    )

# ---------------- COMMANDS ----------------

runtime_context = SimpleNamespace(
    # IDs / paths
    WAR_CHANNEL_ID=WAR_CHANNEL_ID,
    FEEDER_WAR_CHANNEL_ID=FEEDER_WAR_CHANNEL_ID,
    CLAN_STATS_CHANNEL_ID=CLAN_STATS_CHANNEL_ID,
    WAR_SUMMARY_CHANNEL_ID=WAR_SUMMARY_CHANNEL_ID,
    LEADER_ROLE_ID=LEADER_ROLE_ID,
    CO_LEADER_ROLE_ID=CO_LEADER_ROLE_ID,
    CLAN_CHAT_CHANNEL_ID=CLAN_CHAT_CHANNEL_ID,
    CLASH_MMO_CHANNEL_ID=CLASH_MMO_CHANNEL_ID,
    MMO_OWNER_ID=MMO_OWNER_ID,
    DATA_DIR=DATA_DIR,
    LINKED_FILE=LINKED_FILE,
    PERFORMANCE_FILE=PERFORMANCE_FILE,
    COINS_FILE=COINS_FILE,
    COIN_LEADERBOARD_IMAGE_PATH=COIN_LEADERBOARD_IMAGE_PATH,
    SHOP_FILE=SHOP_FILE,
    SHOP_ITEMS=SHOP_ITEMS,
    LOOT_DROP_FILE=LOOT_DROP_FILE,
    LOOT_DROP_STYLES=LOOT_DROP_STYLES,
    LOOT_DROP_MIN_MINUTES=LOOT_DROP_MIN_MINUTES,
    LOOT_DROP_MAX_MINUTES=LOOT_DROP_MAX_MINUTES,
    # State / storage helpers
    safe_load_json=safe_load_json,
    safe_save_json=safe_save_json,
    update_json_file=update_json_file,
    file_lock=file_lock,
    loot_drop_lock=loot_drop_lock,
    economy=economy,
    # Clash helpers
    get_current_war=get_current_war,
    get_war_league_group=get_war_league_group,
    get_cwl_round_war=get_cwl_round_war,
    get_clan_members=get_clan_members,
    get_clan_info=get_clan_info,
    get_clan_member=get_clan_member,
    get_opponent_member=get_opponent_member,
    build_war_embed=build_war_embed,
    build_cwl_embed=build_cwl_embed,
    apply_war_rewards=apply_war_rewards,
    evaluate_attack=evaluate_attack,
    build_reward_embed=build_reward_embed,
    post_current_war_update=post_current_war_update,
    post_donation_update=post_donation_update,
    check_war_end=check_war_end,
    post_clutch_summary_command=post_clutch_summary_command,
    reset_war_pings=reset_war_pings,
    # Misc helpers
    normalize_tag=normalize_tag,
    normalize_linked_data=normalize_linked_data,
    safe_int=safe_int,
    render_html_to_png_buffer=render_html_to_png_buffer,
    # Loot drop service
    create_loot_drop=loot_drops.create_loot_drop,
    load_loot_drop=loot_drops.load_loot_drop,
    claim_loot_drop=loot_drops.claim_loot_drop,
    schedule_next_loot_drop=loot_drops.schedule_next_loot_drop,
)

economy.runtime_context = runtime_context
economy.mmo_ctx = runtime_context

# Register command modules
register_all_commands(bot, runtime_context)
register_clan_snapshot_command(bot, runtime_context)
register_current_progress_command(bot, runtime_context)

# ---------------- READY ----------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        guild_ids = os.getenv("SYNC_GUILD_IDS", "").strip()
        if guild_ids:
            for raw in guild_ids.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                guild = discord.Object(id=int(raw))
                synced = await bot.tree.sync(guild=guild)
                print(f"Synced {len(synced)} commands to guild {raw}")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global commands")
    except Exception as e:
        print("Command sync failed:", e)
        traceback.print_exc()

    if not update_loop.is_running():
        update_loop.start()

    # Start loot drop scheduler
    bot.loop.create_task(loot_drops.loot_drop_loop(bot, runtime_context))

# ---------------- SHUTDOWN ----------------

async def shutdown():
    await close_session()
    await bot.close()


def handle_signal():
    asyncio.create_task(shutdown())

try:
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass
except RuntimeError:
    pass

# ---------------- RUN ----------------

bot.run(DISCORD_TOKEN)
