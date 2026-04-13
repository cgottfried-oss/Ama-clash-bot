# ---------------- ENVIRONMENT ----------------
import os
import json
import aiohttp
import asyncio
import re
import traceback
from datetime import datetime, timezone, timedelta
from collections import defaultdict

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
CLAN_TAG = require_env("CLAN_TAG")
WAR_CHANNEL_ID = require_int_env("WAR_CHANNEL_ID")
CLAN_STATS_CHANNEL_ID = require_int_env("LEADERBOARD_CHANNEL_ID")
WAR_SUMMARY_CHANNEL_ID = require_int_env("WAR_SUMMARY_CHANNEL_ID")
LEADER_ROLE_ID = require_int_env("LEADER_ROLE_ID")
CO_LEADER_ROLE_ID = require_int_env("CO_LEADER_ROLE_ID")

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
PERFORMANCE_FILE = os.path.join(DATA_DIR, "player_performance.json")
WAR_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "war_template.html")
FINAL_WAR_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "final_war_template.html")
FINAL_WAR_IMAGE_PATH = "/app/final_war.png"
DONATION_TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "donation_template.html")
DONATION_IMAGE_PATH = "/app/donations.png"
MONTHLY_MVP_FILE = os.path.join(DATA_DIR, "monthly_mvp.json")

TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$")
HEADERS = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}

# ---------------- DISCORD ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ---------------- GLOBALS/COOLDOWNS ----------------
session: aiohttp.ClientSession | None = None
api_cache = {}
file_lock = asyncio.Lock()

# ---------------- HELPER FUNCTIONS ----------------
async def safe_load_json(path):
    async with file_lock:
        if not os.path.exists(path):
            return {}

        def _read():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"[JSON LOAD ERROR] Invalid JSON in {path}: {e}")
                return {}
            except Exception as e:
                print(f"[JSON LOAD ERROR] Could not read {path}: {e}")
                return {}

        return await asyncio.to_thread(_read)


async def safe_save_json(path, data):
    """Save JSON asynchronously, safely handling file writes."""
    async with file_lock:

        def _write():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving JSON to {path}: {e}")

        await asyncio.to_thread(_write)


async def update_json_file(path, update_fn):
    """
    Safely load, modify, and save a JSON file under one lock.
    update_fn receives the current data and must return the updated data.
    """
    async with file_lock:
        if not os.path.exists(path):
            data = {}
        else:

            def _read():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    print(f"[JSON LOAD ERROR] Invalid JSON in {path}: {e}")
                    return {}
                except Exception as e:
                    print(f"[JSON LOAD ERROR] Could not read {path}: {e}")
                    return {}

            data = await asyncio.to_thread(_read)

        updated_data = update_fn(data)

        def _write():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Error saving JSON to {path}: {e}")

        await asyncio.to_thread(_write)
        return updated_data


async def reset_war_pings():
    await safe_save_json(WAR_PINGS_FILE, {"start": [], "12h": [], "1h": [], "end": []})


def normalize_tag(tag: str) -> str:
    return tag.strip().upper().replace("O", "0")


def normalize_linked_data(linked: dict) -> dict:
    normalized = {}

    for user_id, entries in linked.items():
        if not isinstance(entries, list):
            entries = [entries]

        clean_entries = []
        for entry in entries:
            if isinstance(entry, str):
                clean_entries.append({"tag": normalize_tag(entry), "name": "Unknown"})
            elif isinstance(entry, dict):
                tag = entry.get("tag")
                if isinstance(tag, str):
                    clean_entries.append(
                        {
                            "tag": normalize_tag(tag),
                            "name": entry.get("name", "Unknown"),
                        }
                    )

        normalized[str(user_id)] = clean_entries

    return normalized


def build_tag_to_discord_map(linked: dict) -> dict:
    tag_to_discord = {}

    for user_id, entries in linked.items():
        for entry in entries:
            tag = entry.get("tag")
            if tag:
                tag_to_discord[tag] = str(user_id)

    return tag_to_discord

# ---------------- CACHE SYSTEM ----------------
CACHE_FILE = os.path.join(DATA_DIR, "api_cache.json")


async def load_cache():
    return await safe_load_json(CACHE_FILE)


async def save_cache(cache):
    await safe_save_json(CACHE_FILE, cache)


async def get_cached_or_fetch(key, url, ttl=120):
    global api_cache
    now = datetime.now(timezone.utc).timestamp()

    if len(api_cache) > 100:
        api_cache = {k: v for k, v in api_cache.items() if now - v["timestamp"] < ttl}

    if key in api_cache:
        entry = api_cache[key]
        if now - entry["timestamp"] < ttl:
            return entry["data"]

    try:
        data = await asyncio.wait_for(fetch_json(url), timeout=10)
    except asyncio.TimeoutError:
        print(f"[CACHE TIMEOUT] Using stale data for {key}")
        return api_cache.get(key, {}).get("data")

    if data:
        api_cache[key] = {"timestamp": now, "data": data}
        await save_cache(api_cache)

    return data


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


async def load_monthly_mvp():
    stored = await safe_load_json(MONTHLY_MVP_FILE)
    season_key = get_season_key()

    if not isinstance(stored, dict):
        return {"season": season_key, "wars": [], "players": {}}

    if stored.get("season") != season_key:
        return {"season": season_key, "wars": [], "players": {}}

    return stored


async def get_current_monthly_mvp():
    stored = await load_monthly_mvp()
    players = stored.get("players", {})

    if not players:
        return None, None

    best_name, best_data = max(
        players.items(),
        key=lambda item: item[1].get("points", 0)
    )
    return best_name, best_data

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


async def fetch_all_data():
    encoded_tag = CLAN_TAG.replace("#", "%23")

    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    war, members_json = await asyncio.gather(
        get_cached_or_fetch("war", war_url, ttl=60),
        get_cached_or_fetch("members", members_url, ttl=300),
    )

    if not war or not members_json:
        print("⚠️ API fetch failed")
        return None, None

    return war, members_json.get("items", [])


from playwright.async_api import async_playwright

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

        # Migrate old format:
        # old: { "#TAG": {...}, "#TAG2": {...} }
        # new: { "season": "2026-04", "players": { "#TAG": {...} } }
        if "season" not in stored or "players" not in stored:
            old_players = {
                k: v for k, v in stored.items()
                if isinstance(v, dict)
            }
            stored = {
                "season": season_key,
                "players": old_players
            }

        # True monthly reset
        if stored.get("season") != season_key:
            print(
                f"[DONATIONS] New month detected. Resetting donations "
                f"from {stored.get('season')} to {season_key}"
            )
            stored = {
                "season": season_key,
                "players": {}
            }

        players = stored.setdefault("players", {})

        for m in members:
            tag = m.get("tag")
            if not tag:
                continue

            players.setdefault(
                tag,
                {"name": m.get("name", "")[:12], "donations": 0, "received": 0}
            )
            players[tag]["name"] = m.get("name", "")[:12]
            players[tag]["donations"] = m.get("donations", 0)
            players[tag]["received"] = m.get("donationsReceived", 0)

        return stored

    stored = await update_json_file(DONATION_FILE, _update_donations)
    leaderboard = sorted(
        stored.get("players", {}).values(),
        key=lambda x: x["donations"],
        reverse=True
    )
    
    monthly_mvp_name, monthly_mvp_data = await get_current_monthly_mvp()

    buffer = await create_donation_image(leaderboard)
    file = discord.File(fp=buffer, filename="donations.png")

    embed = discord.Embed(
        title=f"Monthly Donations - {season_key}",
        color=0x2C2F33
    )

    if monthly_mvp_name and monthly_mvp_data:
        embed.description = (
            f"🏆 **Monthly MVP:** {monthly_mvp_name}\n"
            f"⭐ {monthly_mvp_data.get('stars', 0)} stars"
            f" • 💥 {monthly_mvp_data.get('destruction', 0):.1f}% destruction"
            f" • 🎯 {monthly_mvp_data.get('triples', 0)} triples"
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


async def process_war_updates(war, members):
    """Main war update dispatcher."""
    await update_war_dashboard(war, members)

# ---------------- UPDATE LOOP ----------------
@tasks.loop(minutes=2)
async def update_loop():
    await asyncio.sleep(1)

    try:
        encoded_tag = CLAN_TAG.replace("#", "%23")
        war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
        members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

        war = await get_cached_or_fetch("war", war_url, ttl=60)
        members_json = await get_cached_or_fetch("members", members_url, ttl=300)
        members = members_json.get("items", []) if members_json else []

        # Always update donations if members loaded
        stats_channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
        if stats_channel and members:
            await update_donation_leaderboard(members, stats_channel)

        # Only do war stuff if war data exists
        if war:
            await process_war_updates(war, members)

    except Exception as e:
        print(f"[UPDATE LOOP ERROR] {e}")
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
        await update_monthly_mvp_from_war(war)
        
        clan_stars = clan.get("stars", 0)
        opp_stars = opponent.get("stars", 0)

        color = 0x2ECC71
        if clan_stars < opp_stars:
            color = 0xE74C3C
        elif clan_stars == opp_stars:
            color = 0xF1C40F

        summary_channel = bot.get_channel(WAR_SUMMARY_CHANNEL_ID)

        if summary_channel:
            buffer = await create_final_war_image(war)
            file = discord.File(fp=buffer, filename="final_war.png")

            embed = discord.Embed(color=color)
            embed.set_image(url="attachment://final_war.png")

            await asyncio.wait_for(
                summary_channel.send(embed=embed, file=file), timeout=10
            )

        await safe_save_json(WAR_END_FILE, {"posted": True})

    # ---------------- CHECK WAR PINGS ----------------
    await check_war_pings(war)
    await check_unlinked_players(war)

# ---------------- LINK COMMAND ----------------
@tree.command(name="link", description="Link your Clash player tag to your Discord")
@app_commands.describe(tag="Enter your Clash player tag (e.g., #ABCD123)")
async def link(interaction: discord.Interaction, tag: str):
    tag = normalize_tag(tag)

    if not TAG_REGEX.match(tag):
        await interaction.response.send_message(
            "❌ Invalid Clash tag! Include # and only use letters A-Z and numbers.",
            ephemeral=True,
        )
        return

    linked = normalize_linked_data(await safe_load_json(LINKED_FILE))
    user_id = str(interaction.user.id)

    existing_entries = linked.get(user_id, [])
    if any(normalize_tag(entry["tag"]) == tag for entry in existing_entries):
        await interaction.response.send_message(
            f"Already linked to {tag}", ephemeral=True
        )
        return

    # ✅ Fetch player data
    encoded_tag = tag.replace("#", "%23")
    url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"

    data = await get_cached_or_fetch(f"player_{tag}", url, ttl=300)

    if not data:
        await interaction.response.send_message(
            "❌ Could not fetch player. Check the tag.", ephemeral=True
        )
        return

    player_name = data.get("name", "Unknown")

    # ✅ Save tag + name atomically
    def _update_linked(data):
        data = normalize_linked_data(data)
        data.setdefault(user_id, [])

        if not any(normalize_tag(entry["tag"]) == tag for entry in data[user_id]):
            data[user_id].append({"tag": tag, "name": player_name})

        return data

    await update_json_file(LINKED_FILE, _update_linked)

    await interaction.response.send_message(
        f"✅ Linked **{player_name}** ({tag})", ephemeral=True
    )

# ---------------- UNLINK COMMAND ----------------
@tree.command(name="unlink", description="Unlink one of your Clash accounts")
@app_commands.describe(tag="Enter the Clash player tag you want to unlink")
async def unlink(interaction: discord.Interaction, tag: str):
    await interaction.response.defer(ephemeral=True)

    tag = normalize_tag(tag)
    user_id = str(interaction.user.id)

    linked_data = normalize_linked_data(await safe_load_json(LINKED_FILE))
    existing_entries = linked_data.get(user_id, [])

    if not existing_entries:
        await interaction.followup.send(
            "❌ You do not have any linked Clash accounts.",
            ephemeral=True,
        )
        return

    if not any(normalize_tag(entry["tag"]) == tag for entry in existing_entries):
        await interaction.followup.send(
            f"❌ {tag} is not currently linked to your Discord.",
            ephemeral=True,
        )
        return

    def _update_unlinked(data):
        data = normalize_linked_data(data)
        entries = data.get(user_id, [])
        data[user_id] = [
            entry for entry in entries if normalize_tag(entry["tag"]) != tag
        ]

        if not data[user_id]:
            data.pop(user_id, None)

        return data

    await update_json_file(LINKED_FILE, _update_unlinked)

    await interaction.followup.send(
        f"✅ Unlinked {tag} from your Discord.",
        ephemeral=True,
    )

# ---------------- LINKED COMMAND ----------------
@tree.command(name="linked", description="View linked Clash accounts")
@app_commands.describe(user="Optional: leaders can check another member")
async def linked(interaction: discord.Interaction, user: discord.Member | None = None):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True,
        )
        return

    # Defer immediately so Discord doesn't think the command failed
    await interaction.response.defer(ephemeral=True)

    linked_data = normalize_linked_data(await safe_load_json(LINKED_FILE))

    if not isinstance(interaction.user, discord.Member):
        await interaction.followup.send(
            "❌ Could not verify your server roles.",
            ephemeral=True,
        )
        return

    is_leader = any(
        role.id in (LEADER_ROLE_ID, CO_LEADER_ROLE_ID)
        for role in interaction.user.roles
    )

    if user is not None and not is_leader:
        await interaction.followup.send(
            "❌ Only leaders and co-leaders can check another member's linked accounts.",
            ephemeral=True,
        )
        return

    target_user = user if user is not None else interaction.user
    user_id = str(target_user.id)

    tags = linked_data.get(user_id, [])

    # Normalize old data
    normalized = []
    for entry in tags:
        if isinstance(entry, str):
            normalized.append({"tag": entry, "name": "Unknown"})
        elif isinstance(entry, dict) and "tag" in entry:
            normalized.append(
                {
                    "tag": entry["tag"],
                    "name": entry.get("name", "Unknown"),
                }
            )

    tags = normalized

    # Refresh names from API
    updated = False
    for entry in tags:
        try:
            encoded_tag = entry["tag"].replace("#", "%23")
            url = f"https://api.clashofclans.com/v1/players/{encoded_tag}"
            data = await get_cached_or_fetch(f"player_{entry['tag']}", url, ttl=3600)

            if data:
                new_name = data.get("name")
                if new_name and new_name != entry["name"]:
                    entry["name"] = new_name
                    updated = True
        except Exception as e:
            print(f"[LINKED REFRESH ERROR] {entry.get('tag')}: {e}")

    if updated:

        def _update_linked_names(data):
            data = normalize_linked_data(data)
            data[user_id] = tags
            return data

        await update_json_file(LINKED_FILE, _update_linked_names)

    entries_text = (
        ", ".join(f"{e['name']} ({e['tag']})" for e in tags) if tags else "None"
    )
    msg = f"{target_user.display_name}'s linked accounts:\n{entries_text}"

    await interaction.followup.send(msg, ephemeral=True)

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

        member_tag = m.get("tag", "").upper()
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
                    normalized_tags.append(tag_value.upper())

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
@tree.command(
    name="linkaudit",
    description="Audit Discord members vs linked Clash accounts vs clan roster",
)
async def linkaudit(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command must be used in a server.", ephemeral=True
        )
        return

    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "❌ Could not verify your server roles.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    roles = [role.id for role in interaction.user.roles]
    is_leader = LEADER_ROLE_ID in roles or CO_LEADER_ROLE_ID in roles

    if not is_leader:
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.", ephemeral=True
        )
        return

    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(
            "❌ This command must be used in a server.", ephemeral=True
        )
        return

    # Ensure member cache is filled
    await guild.chunk()

    linked_raw = await safe_load_json(LINKED_FILE)
    linked = normalize_linked_data(linked_raw)

    war, clan_members = await fetch_all_data()
    if clan_members is None:
        await interaction.followup.send(
            "❌ Could not fetch current clan members from the Clash API.",
            ephemeral=True,
        )
        return

    clan_lookup = []
    clan_tags = set()

    for m in clan_members:
        tag = normalize_tag(m.get("tag", ""))
        name = m.get("name", "Unknown")
        if tag:
            clan_lookup.append({"tag": tag, "name": name})
            clan_tags.add(tag)

    tag_to_discord = build_tag_to_discord_map(linked)

    unlinked_discord = []
    linked_not_in_clan = []
    linked_in_clan = []
    clan_not_linked = []
    kick_candidates = []

    # Compare all Discord members
    for member in guild.members:
        if member.bot:
            continue

        user_id = str(member.id)
        entries = linked.get(user_id, [])
        linked_tags = [e["tag"] for e in entries if e.get("tag")]

        if not linked_tags:
            unlinked_discord.append(member)
            kick_candidates.append((member, "No linked Clash account"))
            continue

        in_clan_tags = [tag for tag in linked_tags if tag in clan_tags]

        if in_clan_tags:
            linked_in_clan.append((member, entries, in_clan_tags))
        else:
            linked_not_in_clan.append((member, entries))
            kick_candidates.append(
                (member, f"Linked, but no linked accounts are in clan")
            )

    # Compare clan roster against linked records
    for m in clan_lookup:
        if m["tag"] not in tag_to_discord:
            clan_not_linked.append(m)

    def format_accounts(entries):
        return ", ".join(
            f"{e.get('name', 'Unknown')} ({e.get('tag', 'Unknown')})" for e in entries
        )

    sections = []

    sections.append("**Kick Candidates**")
    if kick_candidates:
        for member, reason in kick_candidates:
            sections.append(f"• {member.display_name} — {reason}")
    else:
        sections.append("• None")

    sections.append("\n**Discord Members With No Link**")
    if unlinked_discord:
        for member in unlinked_discord:
            sections.append(f"• {member.display_name}")
    else:
        sections.append("• None")

    sections.append("\n**Linked Discord Members Not In Clan**")
    if linked_not_in_clan:
        for member, entries in linked_not_in_clan:
            sections.append(f"• {member.display_name} — {format_accounts(entries)}")
    else:
        sections.append("• None")

    sections.append("\n**Clan Members Not Linked To Discord**")
    if clan_not_linked:
        for m in clan_not_linked:
            sections.append(f"• {m['name']} ({m['tag']})")
    else:
        sections.append("• None")

    sections.append("\n**Linked And In Clan**")
    if linked_in_clan:
        for member, entries, in_clan_tags in linked_in_clan:
            matching = [e for e in entries if e.get("tag") in in_clan_tags]
            sections.append(f"• {member.display_name} — {format_accounts(matching)}")
    else:
        sections.append("• None")

    report = "\n".join(sections)

    # Split long reports
    chunk_size = 1900
    for i in range(0, len(report), chunk_size):
        await interaction.followup.send(report[i : i + chunk_size], ephemeral=True)


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

    if not refresh_session.is_running():
        refresh_session.start()


# Safe shutdown function
async def shutdown():
    print("Shutting down bot and closing HTTP session...")
    await close_session()

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
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received.")
    finally:
        # Ensure session closes on exit
        asyncio.run(shutdown())
