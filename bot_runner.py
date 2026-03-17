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
LOGO_PATH = os.path.join(ASSETS_DIR, "clan_logo.png")
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


# ---------------- HTTP Session Management ----------------
async def get_session():
    global session
    if session is None or session.closed:
        session = aiohttp.ClientSession()
    return session


async def close_session():
    global session
    if session and not session.closed:
        await session.close()
        session = None


# ---------------- Clash API ----------------
async def fetch_json(url):
    sess = await get_session()
    try:
        async with sess.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status != 200:
                return None
            return await r.json()
    except aiohttp.ClientError as e:
        print(f"Clash API request failed: {e}")
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
def generate_attack_suggestions(war):
    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    clan_members = clan.get("members", [])
    opponent_members = opponent.get("members", [])

    suggestions = []
    assigned_targets = {}  # Tracks how many times a target has been assigned
    max_attacks_per_target = 2  # Each target can be recommended at most twice

    # Sort attackers by performance: stars then destruction
    def attacker_score(m):
        attacks = m.get("attacks", [])
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        return (stars, destruction)

    sorted_attackers = sorted(clan_members, key=attacker_score, reverse=True)

    for attacker in sorted_attackers:
        attacks_done = len(attacker.get("attacks", []))
        attacks_needed = 2 - attacks_done
        if attacks_needed <= 0:
            continue

        attacker_th = attacker.get("townhallLevel")
        attacker_name = attacker.get("name")

        attacker_targets = []

        for _ in range(attacks_needed):
            # Shuffle opponents each time to randomize tie-breaks
            candidates = opponent_members.copy()
            random.shuffle(candidates)

            best_target = None
            smallest_gap = 99

            for target in candidates:
                target_th = target.get("townhallLevel") or 0
                target_pos = target.get("mapPosition")

                # 🚫 Skip bases already 3-starred
                best_attack = target.get("bestOpponentAttack")
                if best_attack and best_attack.get("stars") == 3:
                    continue

                # Skip if target already assigned max times or already assigned to this attacker
                if assigned_targets.get(target_pos, 0) >= max_attacks_per_target:
                    continue
                if target_pos in attacker_targets:
                    continue
                
                if best_target is None:
                    # fallback: allow already-hit bases if nothing else available
                    for target in candidates:
                        target_pos = target.get("mapPosition")
                        if assigned_targets.get(target_pos, 0) < max_attacks_per_target:
                            best_target = target_pos
                            break

                th_gap = abs(attacker_th - target_th)
                # Slight random factor to break ties
                th_gap_adjusted = th_gap + random.uniform(0, 0.5)

                if th_gap_adjusted < smallest_gap:
                    smallest_gap = th_gap_adjusted
                    best_target = target_pos

            if best_target is not None:
                attacker_targets.append(best_target)
                assigned_targets[best_target] = assigned_targets.get(best_target, 0) + 1
            else:
                break # No valid targets left

        for t in attacker_targets:
            suggestions.append(
                f"⚔️ {attacker_name} → Recommended target #{t}"
            )

    return suggestions[:10]  # Show top 10 suggestions

last_state = {}
last_war_id = None

@tasks.loop(minutes=2)
async def update_loop():
    await asyncio.sleep(1)
    global last_state, last_war_id

    try:
        encoded_tag = CLAN_TAG.replace("#", "%23")
        war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
        members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

        # -------- Fetch Data --------
        war = await fetch_json(war_url)
        members_json = await fetch_json(members_url)

        if not war or not members_json:
            return

        clan = war.get("clan")
        opponent = war.get("opponent")

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
    suggestions = generate_attack_suggestions(war)
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

# Add suggestions ONCE
    if clean_suggestions:
        embed.add_field(
            name="🧠 Smart Attack Suggestions",
            value="\n".join(clean_suggestions),
            inline=False,
        )
    else:
        embed.add_field(
            name="🧠 Smart Attack Suggestions",
            value="No suggestions available yet.",
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

        await channel.send(embed=summary)
        await safe_save_json(WAR_END_FILE, {"posted": True})

    # ---------------- Update Donations Leaderboard ----------------
    stats_channel = bot.get_channel(CLAN_STATS_CHANNEL_ID)
    if stats_channel:
        await update_donation_leaderboard(full_members, stats_channel)

    # ---------------- Check War Pings ----------------
    await check_war_pings(war)
    await check_unlinked_players(war)

# ------------- Recruitment Command ----------------
@tree.command(name="recruit", description="Generate shareable recruitment text with banner")
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

    # ---------------- Fetch Clan Data with Timeout ----------------
    clan_data = None
    encoded_tag = CLAN_TAG.replace("#", "%23")
    clan_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}"
    sess = await get_session()
    try:
        async with sess.get(clan_url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                await interaction.followup.send(
                    "Clash API error retrieving clan data.", ephemeral=True
                )
                return
            clan_data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        await interaction.followup.send(f"Clash API error: {e}", ephemeral=True)
        return
                clan_data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        await interaction.followup.send(f"Clash API error: {e}", ephemeral=True)
        return

    if not clan_data or "reason" in clan_data:
        await interaction.followup.send("Clash API returned an error.", ephemeral=True)
        return

    clan_name = clan_data.get("name", "Our Clan")
    tag = clan_data.get("tag", "")

    # ---------------- Generate Recruitment Image ----------------
    try:
        image = await asyncio.to_thread(generate_recruitment_image, clan_data)
    except Exception as e:
        print("Image generation failed:", e)
        image = BytesIO()
        fallback = Image.new("RGBA", (1000, 400), (0, 0, 0, 255))
        fallback.save(image, format="PNG")
        image.seek(0)
    file = discord.File(fp=image, filename="recruit.png")

    # ---------------- Generate Copyable Messages Safely ----------------
    openers = [
        "Looking for an active clan?",
        "Searching for a strong war clan?",
        "Need a new Clash home?",
        "Ready to dominate wars?",
        "Looking for a chill but competitive clan?",
    ]
    features = [
        "Active donations",
        "War participation",
        "CWL lineup",
        "Monthly leaderboards",
        "Organized leadership",
    ]
    closers = [
        "Join today!",
        "Apply now!",
        "Come clash with us!",
        "Your next clan awaits!",
        "We’re recruiting now!",
    ]

    combos = set()
    attempts = 0
    while len(combos) < 5 and attempts < 20:  # safety cap to avoid infinite loop
        message = f"{random.choice(openers)} {random.choice(features)}. {random.choice(closers)}"
        combos.add(message)
        attempts += 1

    copy_block = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(combos)])

    # ---------------- Build Plain Text Output ----------------
    text_output = (
        f"⚔️ Join {clan_name} ⚔️\n"
        "A relaxed but competitive Clash clan with active donations, war, and CWL participation.\n\n"
        f"💬 Recruitment Messages:\n{copy_block}\n\n"
        "🌟 What We Offer:\n"
        "- Friendly, active community\n"
        "- War & CWL participation\n"
        "- Monthly leaderboards\n"
        "- Discord integration\n\n"
        "✅ Requirements:\n"
        "- TH13+\n"
        "- Active players\n"
        "- War participation\n\n"
        f"Join today and dominate wars with {clan_name.split('–')[0]}!\n"
        f"View Clan: https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}"
    )

    # ---------------- Minimal Embed for Visual Banner ----------------
    embed = discord.Embed(
        title=f"Join {clan_name} – AMA",
        description=None,
        color=0xFFA500,
    )
    embed.set_image(url="attachment://recruit.png")  # only banner

    # ---------------- View Button ----------------
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="View Clan",
            url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}",
        )
    )

    # ---------------- Send Message ----------------
    await interaction.followup.send(
        content=f"```\n{text_output}\n```", embed=embed, file=file, view=view
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
