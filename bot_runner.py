# ---------------- Environment ----------------
import os
import json
import aiohttp
import asyncio
import re
import random
import traceback
from datetime import datetime, timezone, timedelta
from io import BytesIO
from collections import defaultdict

import discord
from discord.ext import tasks, commands
from discord import app_commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load .env
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLASH_API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")
WAR_CHANNEL_ID = int(os.getenv("WAR_CHANNEL_ID"))
CLAN_STATS_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))
LEADER_ROLE_ID = int(os.getenv("LEADER_ROLE_ID"))
CO_LEADER_ROLE_ID = int(os.getenv("CO_LEADER_ROLE_ID"))

# ---------------- Paths ----------------
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
ASSETS_DIR = "/app/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

BANNER_PATH = os.path.join(ASSETS_DIR, "clan_banner.png")
UNLINKED_WARN_FILE = os.path.join(DATA_DIR, "unlinked_warned.json")
WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
DONATION_FILE = os.path.join(DATA_DIR, "donations.json")
CWL_FILE = os.path.join(DATA_DIR, "cwl_data.json")
MISSED_FILE = os.path.join(DATA_DIR, "missed_attacks.json")
MVP_FILE = os.path.join(DATA_DIR, "mvp_data.json")
ASSIGN_FILE = os.path.join(DATA_DIR, "war_assignments.json")
LINKED_FILE = os.path.join(DATA_DIR, "linked_players.json")
WAR_PINGS_FILE = os.path.join(DATA_DIR, "war_pings.json")
WAR_END_FILE = os.path.join(DATA_DIR, "war_end.json")
PERFORMANCE_FILE = os.path.join(DATA_DIR, "player_performance.json")

TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$")
HEADERS = {"Authorization": f"Bearer {CLASH_API_KEY}", "Accept": "application/json"}

# ---------------- Discord ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ---------------- Globals / Cooldowns ----------------
session: aiohttp.ClientSession | None = None
recruit_cooldown: dict[int, float] = {}  # <--- added cooldown dict


# ---------------- Helper Functions ----------------
def create_bar(value, max_value, length=10):
    if max_value <= 0:
        return "░" * length
    filled = int((value / max_value) * length) if max_value else 0
    return "█" * filled + "░" * (length - filled)


def chunk_list(lst, n):
    """Split a list into chunks of size n."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def safe_load_json(path):
    """Load JSON asynchronously, return empty dict if file missing or error occurs."""
    if not os.path.exists(path):
        return {}

    def _read():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    return await asyncio.to_thread(_read)


async def safe_save_json(path, data):
    """Save JSON asynchronously, safely handling file writes."""

    def _write():
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving JSON to {path}: {e}")

    await asyncio.to_thread(_write)

async def load_performance():
    return await safe_load_json(PERFORMANCE_FILE)

async def save_performance(data):
    await safe_save_json(PERFORMANCE_FILE, data)


# ---------------- HTTP Session Management ----------------
async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
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
            async with sess.get(
                url,
                headers=HEADERS
            ) as r:

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


async def update_donation_leaderboard(members, channel: discord.TextChannel):
    if not channel:
        return
    stored = await safe_load_json(DONATION_FILE)
    current_total = sum(m.get("donations", 0) for m in members)
    stored_total = sum(v.get("donations", 0) for v in stored.values())
    if stored_total > 0 and current_total < stored_total * 0.2:
        stored = {}

    for m in members:
        tag = m.get("tag")
        if not tag:
            continue  # skip members without tag

        stored.setdefault(tag, {"name": m.get("name", "")[:12], "donations": 0, "received": 0})
        stored[tag]["name"] = m.get("name", "")[:12]
        stored[tag]["donations"] = m.get("donations", 0)
        stored[tag]["received"] = m.get("donationsReceived", 0)

    await safe_save_json(DONATION_FILE, stored)

    # Build leaderboard embed
    leaderboard = sorted(stored.values(), key=lambda x: x["donations"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]
    rows = []
    max_don = max([m["donations"] for m in leaderboard] + [1])
    for i, m in enumerate(leaderboard[:10]):
        bar = create_bar(m["donations"], max_don, 12)
        if i == 0:
            rows.append(f"{medals[0]} **{m['name']} 👑**\n`{bar}` **{m['donations']}** | Received: {m['received']}")
        elif i < 3:
            rows.append(f"{medals[i]} **{m['name']}**\n`{bar}` {m['donations']} | Received: {m['received']}")
        else:
            rows.append(f"• {m['name']}\n`{bar}` {m['donations']} | Received: {m['received']}")

    embed = discord.Embed(
        title="📊 Clan Donation Leaderboard",
        description="\n\n".join(rows),
        color=0xF1C40F,
    )
    embed.set_footer(text="Live donation rankings • Updates automatically")

    mid = await get_saved_message(LEADERBOARD_MESSAGE_FILE)
    msg = None
    if mid:
        try:
            msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            msg = None
    if msg:
        await msg.edit(embed=embed)
    else:
        new_msg = await channel.send(embed=embed)
        await save_message(LEADERBOARD_MESSAGE_FILE, new_msg.id)

# ---------------- CWL / MVP ----------------
async def update_cwl_stats(members):
    cwl = await safe_load_json(CWL_FILE)
    for m in members:
        name = m["name"]
        attacks = m.get("attacks", [])
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        if name not in cwl:
            cwl[name] = {"stars": 0, "destruction": 0, "attacks": 0}
        cwl[name]["stars"] = stars
        cwl[name]["destruction"] = destruction
        cwl[name]["attacks"] = len(attacks)
    await safe_save_json(CWL_FILE, cwl)


async def track_missed_attacks(members, attacks_per_member):
    missed = await safe_load_json(MISSED_FILE)
    for m in members:
        name = m["name"]
        used = len(m.get("attacks", []))
        if used < attacks_per_member:
            if name not in missed:
                missed[name] = 0
            missed[name] += 1
    await safe_save_json(MISSED_FILE, missed)


async def update_mvp(members):
    mvp = await safe_load_json(MVP_FILE)
    for m in members:
        name = m["name"]
        stars = sum(a.get("stars", 0) for a in m.get("attacks", []))
        donations = m.get("donations", 0)
        if name not in mvp:
            mvp[name] = {"stars": 0, "donations": 0, "attacks": 0}
        mvp[name]["stars"] += stars
        mvp[name]["donations"] += donations
        mvp[name]["attacks"] += len(m.get("attacks", []))
    await safe_save_json(MVP_FILE, mvp)


# ---------------- AI Attack Suggestions ----------------
async def generate_attack_suggestions(war):
    from datetime import datetime, timezone

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    clan_members = clan.get("members", [])
    opponent_members = opponent.get("members", [])
    
    performance = await load_performance()

    suggestions = []
    assignments = []
    assigned_targets = {}
    max_attacks_per_target = 2

    # ---------------- WAR PHASE ----------------
    state = war.get("state")
    end_time = war.get("endTime")

    hours_left = 24
    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        remaining = end_dt - datetime.now(timezone.utc)
        hours_left = remaining.total_seconds() / 3600

    # Phase logic
    if hours_left > 12:
        phase = "early"
    elif hours_left > 3:
        phase = "mid"
    else:
        phase = "late"

    # ---------------- PLAYER PERFORMANCE ----------------
    def player_score(m):
        name = m.get("name")

        attacks = m.get("attacks", [])
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        base = stars * 100 + destruction

        # 🧠 Historical performance boost
        if name in performance:
            data = performance[name]

            if data["attacks"] > 0:
                triple_rate = data["triples"] / data["attacks"]
                fail_rate = data["fails"] / data["attacks"]

                base += triple_rate * 200   # reward good attackers
                base -= fail_rate * 150     # punish bad attackers

        return base 

    # ---------------- TARGET SCORING ----------------
    def score_target(attacker_th, target):
        target_th = target.get("townhallLevel") or 0
        best = target.get("bestOpponentAttack")

        # Skip 3-star
        if best and best.get("stars") == 3:
            return -1

        stars = best.get("stars", 0) if best else 0
        destruction = best.get("destructionPercentage", 0) if best else 0

        score = 0

        # -------- Phase-Based Priority --------
        if phase == "early":
            # prioritize fresh hits
            if stars == 0:
                score += 200
            elif stars == 1:
                score += 100
            else:
                score += 50

        elif phase == "mid":
            # balanced
            if stars == 2:
                score += 250 + destruction
            elif stars == 1:
                score += 180
            else:
                score += 120

        else:  # late war
            # ONLY cleanup matters
            if stars == 2:
                # Only worth it if high % (close cleanup)
                if destruction >= 85:
                    score += 400 + destruction
                else:
                    score += 150
            elif stars == 1:
                score += 250
            else:
                score += 50

        # TH gap penalty
        th_gap = abs(attacker_th - target_th)
        score -= th_gap * 30

        return score

        
    # Sort attackers by performance (best first)
    sorted_attackers = sorted(
        clan_members,
        key=lambda m: player_score(m),
        reverse=True
        )

    # ---------------- ASSIGNMENT SYSTEM ----------------
    for attacker in sorted_attackers:
        attacks_done = len(attacker.get("attacks", []))
        attacks_left = 2 - attacks_done
        if attacks_left <= 0:
            continue

        attacker_name = attacker.get("name")
        attacker_th = attacker.get("townhallLevel")

        # Track targets this player already hit
        attacked_tags = {
            attack.get("defenderTag")
            for attack in attacker.get("attacks", [])
        }

        attacker_targets = []

        for _ in range(attacks_left):
            best_target = None
            best_score = -999

            for target in opponent_members:
                pos = target.get("mapPosition")

                # Prefer NOT to re-hit same base, but allow if needed
                is_repeat = target.get("tag") in attacked_tags

                # 🚫 Skip targets this attacker already hit
                already_attacked = False
                for attack in attacker.get("attacks", []):
                    if attack.get("defenderTag") == target.get("tag"):
                        already_attacked = True
                        break

            if already_attacked:
                continue

                if assigned_targets.get(pos, 0) >= max_attacks_per_target:
                    continue
                if pos in attacker_targets:
                    continue

                score = score_target(attacker_th, target)

                # Apply penalty if it's a repeat hit
                if is_repeat:
                    score -= 100

                if score > best_score:
                    best_score = score
                    best_target = target

            if best_target:
                pos = best_target.get("mapPosition")
                attacker_targets.append(pos)
                assigned_targets[pos] = assigned_targets.get(pos, 0) + 1

        # ---------------- OUTPUT ----------------

        if not attacker_targets:
            # fallback: closest TH target
            fallback = min(
                opponent_members,
                key=lambda t: abs((attacker_th or 0) - (t.get("townhallLevel") or 0))
            )
            attacker_targets = [fallback.get("mapPosition")]

        if attacker_targets:
            # FIRST target = priority hit
            first = attacker_targets[0]
            others = attacker_targets[1:]

            msg = f"⚔️ {attacker_name} → Recommended target #{first}"
            if others:
                msg += f" (backup: {', '.join('#'+str(x) for x in others)})"

            suggestions.append(msg)

            # Assignment tracking (for future expansion)
            assignments.append({
                "player": attacker_name,
                "primary": first,
                "backup": others
            })

    # ---------------- HIT ORDER LOGIC ----------------
    # Top players hit first
    hit_order = [m.get("name") for m in sorted_attackers[:5]]

    # ---------------- WIN PREDICTOR ----------------
    clan_stars = clan.get("stars", 0)
    opp_stars = opponent.get("stars", 0)

    clan_attacks = clan.get("attacks", 0)
    opp_attacks = opponent.get("attacks", 0)

    total_attacks = war.get("teamSize", 0) * war.get("attacksPerMember", 2)

    clan_efficiency = clan_stars / clan_attacks if clan_attacks else 0
    opp_efficiency = opp_stars / opp_attacks if opp_attacks else 0

    attacks_left_clan = total_attacks - clan_attacks
    attacks_left_opp = total_attacks - opp_attacks

    projected_clan = clan_stars + (attacks_left_clan * clan_efficiency)
    projected_opp = opp_stars + (attacks_left_opp * opp_efficiency)

    win_chance = 50
    if projected_clan > projected_opp:
        win_chance = min(90, 50 + (projected_clan - projected_opp) * 5)
    else:
        win_chance = max(10, 50 - (projected_opp - projected_clan) * 5)

    # ---------------- FINAL OUTPUT ----------------
    return {
        "suggestions": suggestions[:10],
        "assignments": assignments,
        "hit_order": hit_order,
        "phase": phase,
        "win_chance": round(win_chance, 1)
    }

last_state = {}
last_war_id = None

# ---------------- UPDATE LOOP ----------------
@tasks.loop(minutes=2)
async def update_loop():
    await asyncio.sleep(1)
    global last_state, last_war_id

    try:
        encoded_tag = CLAN_TAG.replace("#", "%23")
        war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
        members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

        # -------- Fetch Data --------
        war, members_json = await asyncio.gather(
            fetch_json(war_url),
            fetch_json(members_url)
        )

        if not war:
            print("⚠️ Failed to fetch war data")
            return

        if not members_json:
            print("⚠️ Failed to fetch member data")
            return

        clan = war.get("clan")
        opponent = war.get("opponent")

        members = members_json.get("items", [])

        #always update leaderboard (even if no war)
        stats_channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
        if stats_channel:
            await update_donation_leaderboard(members, stats_channel)
        
        #if not in war, stop here
        if not clan or not opponent:
            return

        members = members_json.get("items", [])

        # -------- Detect War Change --------
        war_id = war.get("preparationStartTime")
        if war_id != last_war_id:
            last_war_id = war_id
            last_state = {}
            await safe_save_json(WAR_END_FILE, {"posted": False})  # reset here

        # -------- Change Detection --------
        current_state = {
            "state": war.get("state"),
            "clan_stars": clan.get("stars"),
            "opp_stars": opponent.get("stars"),
            "clan_attacks": clan.get("attacks"),
            "opp_attacks": opponent.get("attacks"),
        }

        if current_state == last_state:
            return  # 🚀 Skip update if nothing changed

        last_state = current_state

        # -------- Build Embed --------
        team_size = war.get("teamSize", 0)
        attacks_per_member = war.get("attacksPerMember", 2)

        clan_stars = clan.get("stars", 0)
        opp_stars = opponent.get("stars", 0)
        clan_destruction = clan.get("destructionPercentage", 0.0)
        opp_destruction = opponent.get("destructionPercentage", 0.0)
        clan_attacks = clan.get("attacks", 0)
        opp_attacks = opponent.get("attacks", 0)
        max_attacks = team_size * attacks_per_member

        # Bars
        star_bar_clan = create_bar(clan_stars, max(clan_stars, opp_stars, 1))
        star_bar_opp = create_bar(opp_stars, max(clan_stars, opp_stars, 1))
        destruction_bar_clan = create_bar(clan_destruction, 100)
        destruction_bar_opp = create_bar(opp_destruction, 100)
        attack_bar_clan = create_bar(clan_attacks, max_attacks)
        attack_bar_opp = create_bar(opp_attacks, max_attacks)

        # Time Remaining
        end_time = war.get("endTime")
        if end_time:
            end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
            remaining = max(end_dt - datetime.now(timezone.utc), timedelta(seconds=0))
            time_remaining = str(remaining).split(".")[0]
        else:
            time_remaining = "N/A"

        # Embed color
        embed_color = 0x95A5A6
        if clan_stars > opp_stars:
            embed_color = 0x2ECC71
        elif clan_stars < opp_stars:
            embed_color = 0xE74C3C

        embed = discord.Embed(
            title=f"⚔️ {clan.get('name')} vs {opponent.get('name')}",
            description=(
                f"State: **{war.get('state')}**\n"
                f"Team Size: **{team_size}v{team_size}**\n"
                f"Time Remaining: **{time_remaining}**\n\n"

                f"⭐ **Score**\n"
                f"🟩 {clan_stars} `{star_bar_clan}`\n"
                f"🟥 {opp_stars} `{star_bar_opp}`\n\n"

                f"💥 **Destruction**\n"
                f"🟩 {clan_destruction:.1f}% `{destruction_bar_clan}`\n"
                f"🟥 {opp_destruction:.1f}% `{destruction_bar_opp}`\n\n"

                f"🔥 **Attacks Used**\n"
                f"🟩 {clan_attacks}/{max_attacks} `{attack_bar_clan}`\n"
                f"🟥 {opp_attacks}/{max_attacks} `{attack_bar_opp}`"
            ),
            color=embed_color,
        )

        # -------- Members (War Data Only) --------
        members_data = []
        for m in clan.get("members", []):
            attacks = m.get("attacks", [])
            members_data.append({
                "tag": m.get("tag"),
                "name": m.get("name")[:12],
                "attacks": len(attacks),
                "stars": sum(a.get("stars", 0) for a in attacks),
                "destruction": sum(a.get("destructionPercentage", 0) for a in attacks),
            })

        # -------- Update Dashboard --------
        await update_war_dashboard(
            war=war,
            members=members_data,
            embed=embed,
            full_members=members  # ✅ pass full clan data here
        )
    except Exception as e:
        print(f"[UPDATE LOOP ERROR] {e}")
        traceback.print_exc()

# ---------------- War Dashboard Updater ----------------
async def update_war_dashboard(war, members, embed, full_members):
    """
    Updates the war dashboard message, attack tracker, smart suggestions,
    donation leaderboard, and posts war end summary if needed.
    """
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    # ---------------- Attack Tracker ----------------
    tracker_rows = []
    attacks_per_member = war.get("attacksPerMember", 2)
    for m in members:
        status = "❌" if m.get("attacks", 0) == 0 else "✅"
        name = m["name"].ljust(12)
        row = f"{status} {name} {m['attacks']}/{attacks_per_member} | {m['stars']}⭐ | {m['destruction']}%"
        tracker_rows.append(row)

    chunks = list(chunk_list(tracker_rows, 10))

    # ---------------- Smart Attack Suggestions ----------------
    data = await generate_attack_suggestions(war)

    suggestions = data["suggestions"]
    phase = data["phase"]
    win_chance = data["win_chance"]
    hit_order = data["hit_order"]
    grouped_suggestions = defaultdict(list)
    for s in suggestions:
        match = re.match(r"⚔️ (.+) → Recommended target #(\d+)", s)
        if not match:
            continue
        if match:
            name, target = match.groups()
            grouped_suggestions[name].append(f"#{target}")

    clean_suggestions = [f"⚔️ {name} → {', '.join(targets)}" for name, targets in grouped_suggestions.items()]

    # ---------------- Add Embed Fields ----------------
    for i, chunk in enumerate(chunks[:24]):
        embed.add_field(
            name="⚔️ Attack Tracker" if i == 0 else "‎",
            value="```\n" + "\n".join(chunk) + "\n```",
            inline=False,
        )

        phase_emoji = {
            "early": "🟢",
            "mid": "🟡",
            "late": "🔴"
        }.get(phase, "⚪")

        embed.add_field(
            name="🧠 War AI",
            value=(
                f"{phase_emoji} Phase: **{phase.upper()}**\n"
                f"📈 Win Chance: **{win_chance}%**\n\n"
                f"🔥 Hit First:\n{', '.join(hit_order[:5])}"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚔️ Attack Plan",
            value="\n".join(suggestions) if suggestions else "No suggestions available.",
            inline=False,
        )

    # ---------------- Send/Edit Dashboard Message ----------------
    mid = await get_saved_message(WAR_MESSAGE_FILE)
    war_msg = None
    if mid:
        try:
            war_msg = await channel.fetch_message(mid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            war_msg = None

    if war_msg:
        try:
            await war_msg.edit(embed=embed)
        except discord.HTTPException:
            pass
    else:
        new_msg = await channel.send(embed=embed)
        await save_message(WAR_MESSAGE_FILE, new_msg.id)

    # ---------------- War End Summary ----------------
    ended_data = await safe_load_json(WAR_END_FILE)
    state = war.get("state", "N/A")
    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    if state == "warEnded" and not ended_data.get("posted"):
        clan_stars = clan.get("stars", 0)
        opp_stars = opponent.get("stars", 0)
        clan_destruction = clan.get("destructionPercentage", 0.0)
        opp_destruction = opponent.get("destructionPercentage", 0.0)

        result = "🏆 Victory!"
        color = 0x2ECC71
        if clan_stars < opp_stars:
            result = "❌ Defeat"
            color = 0xE74C3C
        elif clan_stars == opp_stars:
            result = "🤝 Draw"
            color = 0xF1C40F

        # Determine MVP
        mvp = None
        best_score = -1
        for m in clan.get("members", []):
            stars = sum(a.get("stars", 0) for a in m.get("attacks", []))
            destruction = sum(a.get("destructionPercentage", 0) for a in m.get("attacks", []))
            score = stars * 100 + destruction
            if score > best_score:
                best_score = score
                mvp = m.get("name")

        summary = discord.Embed(
            title="🏁 War Finished",
            description=f"**{clan.get('name', 'Clan')} vs {opponent.get('name', 'Opponent')}**",
            color=color,
        )
        summary.add_field(
            name="Result",
            value=f"{result}\n⭐ {clan_stars} - {opp_stars}\n💥 {clan_destruction:.1f}% - {opp_destruction:.1f}%",
            inline=False,
        )
        if mvp:
            summary.add_field(name="🏅 War MVP", value=mvp)

        performance = await load_performance()

        for m in clan.get("members", []):
            name = m.get("name")
            attacks = m.get("attacks", [])

            if name not in performance:
                performance[name] = {
                    "stars": 0,
                    "attacks": 0,
                    "triples": 0,
                    "fails": 0
                }

            for a in attacks:
                stars = a.get("stars", 0)

                performance[name]["stars"] += stars
                performance[name]["attacks"] += 1

                if stars == 3:
                    performance[name]["triples"] += 1
                elif stars <= 1:
                    performance[name]["fails"] += 1

        await save_performance(performance)

        await channel.send(embed=summary)
        await safe_save_json(WAR_END_FILE, {"posted": True})

    # ---------------- Update Donations Leaderboard ----------------
    stats_channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
    if stats_channel:
        await update_donation_leaderboard(full_members, stats_channel)

    # ---------------- Check War Pings ----------------
    await check_war_pings(war)
    await check_unlinked_players(war)

    # ---------------- Recruit Command ----------------

@tree.command(name="recruit", description="Generate high-conversion recruitment messages")
async def recruit(interaction: discord.Interaction):
    user_id = interaction.user.id
    now = datetime.now().timestamp()

    # ---------------- Cooldown ----------------
    if user_id in recruit_cooldown and now - recruit_cooldown[user_id] < 20:
        await interaction.response.send_message(
            "Please wait before using this again.", ephemeral=True
        )
        return
    recruit_cooldown[user_id] = now

    # ---------------- Permission Check ----------------
    roles = [role.id for role in interaction.user.roles]
    if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.defer()

    # ---------------- Fetch Clan Data ----------------
    encoded_tag = CLAN_TAG.replace("#", "%23")
    clan_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}"
    sess = await get_session()

    try:
        async with sess.get(clan_url, headers=HEADERS) as resp:
            if resp.status != 200:
                await interaction.followup.send("Error retrieving clan data.", ephemeral=True)
                return
            clan_data = await resp.json()
    except Exception as e:
        await interaction.followup.send(f"API error: {e}", ephemeral=True)
        return

    clan_name = clan_data.get("name", "Our Clan")
    tag = clan_data.get("tag", "")
    clan_level = clan_data.get("clanLevel", "?")
    members = clan_data.get("members", "?")

    link = f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}"

    # ---------------- Message Variations ----------------

    hooks = [
        "Tired of dead clans?",
        "Looking for a clan that actually shows up to war?",
        "Need a solid crew for wars and CWL?",
        "Done carrying inactive players?",
        "Want a clan that actually donates and attacks?"
    ]

    vibes = [
        "We’re chill, but we take wars seriously.",
        "Relaxed environment, competitive mindset.",
        "No drama, just solid players getting better.",
        "We keep it fun, but we play to win.",
    ]

    urgency = [
        "Spots fill fast.",
        "Looking for a few strong players.",
        "Only accepting active members right now.",
        "Now’s a good time to join before next war.",
    ]

    # ---------------- Discord Style ----------------
    discord_msg = (
        f"⚔️ **{clan_name} [Lvl {clan_level}]** ⚔️\n\n"
        f"{random.choice(hooks)}\n\n"
        f"{random.choice(vibes)}\n\n"
        "**🔥 What you get:**\n"
        "• Constant wars\n"
        "• CWL lineup\n"
        "• Fast donations\n"
        "• Active players\n\n"
        "**✅ What we expect:**\n"
        "• TH13+\n"
        "• Use both attacks\n"
        "• Stay active\n\n"
        f"👥 Members: {members}/50\n"
        f"⏳ {random.choice(urgency)}\n\n"
        f"👉 {link}"
    )

    # ---------------- Reddit Style ----------------
    reddit_msg = (
        f"{clan_name} (Level {clan_level}) is recruiting\n\n"
        f"{random.choice(vibes)}\n\n"
        "What we offer:\n"
        "- War + CWL\n"
        "- Active donations\n"
        "- Consistent activity\n\n"
        "Requirements:\n"
        "- TH13+\n"
        "- Uses both attacks\n"
        "- Active\n\n"
        f"{random.choice(urgency)}\n\n"
        f"Join: {link}"
    )

    # ---------------- Short / Spam-Friendly ----------------
    short_msg = random.choice([
        f"{clan_name} | Lvl {clan_level} | War + CWL | Active | TH13+ 👉 {link}",
        f"Active war clan recruiting (TH13+) ⚔️ {clan_name} 👉 {link}",
        f"{clan_name} recruiting | Chill + Competitive | TH13+ 👉 {link}",
    ])

    # ---------------- DM / Personal Recruit ----------------
    dm_msg = (
        f"Hey! If you're still looking for a clan, check us out 👇\n\n"
        f"⚔️ {clan_name} (Lvl {clan_level})\n"
        "Active, good donations, and we take wars seriously.\n\n"
        f"Join here: {link}"
    )

    # ---------------- Send ----------------
    await interaction.followup.send(
        f"**📋 Copy & Paste (High Conversion Recruit Messages)**\n\n"

        f"**🔥 Discord Post:**\n```\n{discord_msg}\n```\n\n"

        f"**📢 Reddit Post:**\n```\n{reddit_msg}\n```\n\n"

        f"**⚡ Short Version:**\n```\n{short_msg}\n```\n\n"

        f"**💬 DM Recruit Message:**\n```\n{dm_msg}\n```"
    )

# ---------------- Link / Linked Commands ----------------
@tree.command(name="link", description="Link your Clash player tag to your Discord")
@app_commands.describe(tag="Enter your Clash player tag (e.g., #ABCD123)")
async def link(interaction: discord.Interaction, tag: str):
    tag = tag.upper()
    if not TAG_REGEX.match(tag):
        await interaction.response.send_message(
            "❌ Invalid Clash tag! Include # and only use letters A-Z and numbers.",
            ephemeral=True,
        )
        return

    linked = await safe_load_json(LINKED_FILE)
    user_id = str(interaction.user.id)
    if user_id not in linked:
        linked[user_id] = []

    if tag in linked[user_id]:
        await interaction.response.send_message(
            f"Already linked to {tag}", ephemeral=True
        )
        return

    linked[user_id].append(tag)
    await safe_save_json(LINKED_FILE, linked)
    await interaction.response.send_message(
        f"✅ Successfully linked your Discord to Clash tag {tag}", ephemeral=True
    )


@tree.command(name="linked", description="View linked Clash accounts")
@app_commands.describe(user="Optional: leaders can check another member")
async def linked(interaction: discord.Interaction, user: discord.Member | None = None):

    linked = await safe_load_json(LINKED_FILE)

    roles = [role.id for role in interaction.user.roles]
    is_leader = LEADER_ROLE_ID in roles or CO_LEADER_ROLE_ID in roles

    if user and is_leader:
        tags = linked.get(str(user.id), [])
        msg = (
            f"{user.display_name}'s linked tags: {', '.join(tags) if tags else 'None'}"
        )
        await interaction.response.send_message(msg, ephemeral=True)
        return

    user_id = str(interaction.user.id)
    tags = linked.get(user_id, [])

    await interaction.response.send_message(
        f"Your linked Clash tags: {', '.join(tags) if tags else 'None'}", ephemeral=True
    )


# ---------------- War Ping Helpers ----------------
async def ping_users_for_interval(interval, members, attacks_per_member):
    pings = await safe_load_json(WAR_PINGS_FILE)
    if interval not in pings:
        pings[interval] = []

    linked = await safe_load_json(LINKED_FILE)
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    messages = []
    for m in members:
        name = m["name"]
        used_attacks = len(m.get("attacks", []))
        if used_attacks >= attacks_per_member:
            continue

        for user_id, tags in linked.items():
            if not isinstance(tags, list):
                tags = [str(tags)]
            member_tag = m.get("tag", "").upper()
            if any(str(tag).upper() == member_tag for tag in tags):
                if user_id not in pings[interval]:
                    if f"<@{user_id}>" not in messages:
                        messages.append(f"<@{user_id}>")
                    pings[interval].append(user_id)

    if messages:
        if interval == "start":
            msg = f"⚔️ **War has started!**\nYou have {attacks_per_member} attacks.\n{' '.join(messages)}"
        elif interval == "12h":
            msg = f"⚠️ **War Reminder (12h remaining)**\nPlayers missing attacks:\n{' '.join(messages)}"
        elif interval == "1h":
            msg = f"🚨 **FINAL WAR REMINDER (1h remaining)**\nPlayers still missing attacks:\n{' '.join(messages)}"
        elif interval == "end":
            msg = f"⏳ **War ending in 5 minutes!**\nLast chance to attack!\n{' '.join(messages)}"
        await channel.send(msg)

    await safe_save_json(WAR_PINGS_FILE, pings)


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

    if start_dt and (now - start_dt) < timedelta(minutes=5):
        await ping_users_for_interval("start", members, war.get("attacksPerMember", 2))
    if timedelta(hours=11, minutes=55) < (end_dt - now) < timedelta(hours=12):
        await ping_users_for_interval("12h", members, war.get("attacksPerMember", 2))
    if timedelta(minutes=55) < (end_dt - now) < timedelta(hours=1):
        await ping_users_for_interval("1h", members, war.get("attacksPerMember", 2))
    if (end_dt - now) < timedelta(minutes=5):
        await ping_users_for_interval("end", members, war.get("attacksPerMember", 2))


async def check_unlinked_players(war):
    members = war.get("clan", {}).get("members", [])
    linked = await safe_load_json(LINKED_FILE)
    warned = await safe_load_json(UNLINKED_WARN_FILE)
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    linked_tags = set()
    for tags in linked.values():
        if not isinstance(tags, list):
            tags = [str(tags)]
        for tag in tags:
            linked_tags.add(tag.upper())

    new_warnings = []
    for m in members:
        tag = m.get("tag", "").upper()
        name = m.get("name")
        if tag and tag not in linked_tags and tag not in warned:
            new_warnings.append(name)
            warned[tag] = True

    if new_warnings:
        msg = (
            "⚠️ **The following war members have NOT linked their Discord:**\n\n"
            + "\n".join(f"• {n}" for n in new_warnings)
            + "\n\nPlease run `/link` in **#ama-clash-link** to enable war reminders."
        )
        await channel.send(msg)

    await safe_save_json(UNLINKED_WARN_FILE, warned)


# ---------------- Bot Events ----------------
@bot.event
async def on_ready():
    await get_session()
    print(f"Bot logged in as {bot.user}")
    await tree.sync()
    update_loop.start()


# Safe shutdown function
async def shutdown():
    print("Shutting down bot and closing HTTP session...")
    await close_session()


# ---------------- Safe Message Helpers ----------------
async def get_saved_message(path):
    """Return saved message ID from file, or None."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except Exception:
        return None


async def save_message(path, message_id):
    """Save message ID to file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(message_id))
    except Exception as e:
        print(f"Error saving message ID to {path}: {e}")


# ---------------- Run Bot ----------------
if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("KeyboardInterrupt received.")
    finally:
        # Ensure session closes on exit
        asyncio.run(shutdown())
