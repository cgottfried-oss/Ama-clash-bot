import os
import json
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import discord
from discord.ext import tasks, commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import asyncio
import re

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CLASH_API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")

WAR_CHANNEL_ID = int(os.getenv("WAR_CHANNEL_ID"))
LEADERBOARD_CHANNEL_ID = int(os.getenv("LEADERBOARD_CHANNEL_ID"))

LEADER_ROLE_ID = int(os.getenv("LEADER_ROLE_ID"))
CO_LEADER_ROLE_ID = int(os.getenv("CO_LEADER_ROLE_ID"))

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

ASSETS_DIR = "/app/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

BANNER_PATH = os.path.join(ASSETS_DIR, "clan_banner.png")
LOGO_PATH = os.path.join(ASSETS_DIR, "clan_logo.png")

UNLINKED_WARN_FILE = os.path.join(DATA_DIR, "unlinked_warned.json")
WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
LAST_DONATIONS_FILE = os.path.join(DATA_DIR, "last_donations.json")
CWL_FILE = os.path.join(DATA_DIR, "cwl_data.json")
MISSED_FILE = os.path.join(DATA_DIR, "missed_attacks.json")
MVP_FILE = os.path.join(DATA_DIR, "mvp_data.json")
ASSIGN_FILE = os.path.join(DATA_DIR, "war_assignments.json")
LINKED_FILE = os.path.join(DATA_DIR, "linked_players.json")
WAR_PINGS_FILE = os.path.join(DATA_DIR, "war_pings.json")
PING_INTERVALS = ["start", "12h", "1h", "end"]

TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$")  # Clash player tag format

headers = {
    "Authorization": f"Bearer {CLASH_API_KEY}",
    "Accept": "application/json"
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# ---------------- Utility ----------------
def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_saved_message(path):
    if os.path.exists(path):
        with open(path) as f:
            return int(f.read().strip())
    return None

def save_message(path, mid):
    with open(path, "w") as f:
        f.write(str(mid))

# ---------------- CWL / MVP ----------------
def update_cwl_stats(members):
    cwl = load_json(CWL_FILE)
    for m in members:
        name = m["name"]
        attacks = m.get("attacks", [])
        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)
        if name not in cwl:
            cwl[name] = {"stars":0,"destruction":0,"attacks":0}
        cwl[name]["stars"] += stars
        cwl[name]["destruction"] += destruction
        cwl[name]["attacks"] += len(attacks)
    save_json(CWL_FILE, cwl)

def track_missed_attacks(members, attacks_per_member):
    missed = load_json(MISSED_FILE)
    for m in members:
        name = m["name"]
        used = len(m.get("attacks", []))
        if used < attacks_per_member:
            if name not in missed:
                missed[name] = 0
            missed[name] += 1
    save_json(MISSED_FILE, missed)

def update_mvp(members):
    mvp = load_json(MVP_FILE)
    for m in members:
        name = m["name"]
        stars = sum(a.get("stars",0) for a in m.get("attacks",[]))
        donations = m.get("donations",0)
        if name not in mvp:
            mvp[name] = {"stars":0,"donations":0,"attacks":0}
        mvp[name]["stars"] += stars
        mvp[name]["donations"] += donations
        mvp[name]["attacks"] += len(m.get("attacks",[]))
    save_json(MVP_FILE, mvp)

# ---------------- Update Loop ----------------
@tasks.loop(minutes=5)
async def update_loop():
    encoded_tag = CLAN_TAG.replace("#","%23")
    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    try:
        war = await asyncio.to_thread(lambda: requests.get(war_url, headers=headers, timeout=10).json())
        members = await asyncio.to_thread(lambda: requests.get(members_url, headers=headers, timeout=10).json()["items"])
    except Exception as e:
        print(f"API error: {e}")
        return

    clan = war.get("clan",{})
    opponent = war.get("opponent",{})
    state = war.get("state","N/A")
    team_size = war.get("teamSize",0)
    attacks_per_member = war.get("attacksPerMember",2)

    await asyncio.to_thread(update_cwl_stats, clan.get("members",[]))
    await asyncio.to_thread(track_missed_attacks, clan.get("members",[]), attacks_per_member)
    await asyncio.to_thread(update_mvp, clan.get("members",[]))

    # ---------------- Generate War Embed ----------------
    end_time = war.get("endTime")
    if end_time:
        end_dt = datetime.strptime(end_time,"%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        time_remaining = str(end_dt - datetime.now(timezone.utc)).split(".")[0]
    else:
        time_remaining = "N/A"

    members_data = []
    total_attacks = 0
    for m in clan.get("members",[]):
        attacks = m.get("attacks",[])
        stars = sum(a.get("stars",0) for a in attacks)
        destruction = sum(a.get("destructionPercentage",0) for a in attacks)
        total_attacks += len(attacks)
        members_data.append({"name":m["name"],"attacks":len(attacks),"stars":stars,"destruction":destruction})

    members_data.sort(key=lambda x:(x["stars"],x["destruction"]), reverse=True)

    medals = ["🥇","🥈","🥉"]
    top, tracker = [],[]
    for i,m in enumerate(members_data):
        if i<3 and m["stars"]>0: top.append(f"{medals[i]} **{m['name']}**")
        warn = " ⚠️" if m["attacks"]==0 else ""
        tracker.append(f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} • {m['stars']}⭐ • {m['destruction']}%{warn}")

    embed = discord.Embed(
        title=f"⚔️ {clan.get('name')} vs {opponent.get('name','Opponent')}",
        description=f"State: **{state}**\nTeam Size: **{team_size}v{team_size}**\nTime Remaining: **{time_remaining}**\n\n🔥 Attacks Used: **{total_attacks}/{team_size*attacks_per_member}**\n⭐ Score: **{clan.get('stars',0)} — {opponent.get('stars',0)}**",
        color=0x2ECC71
    )
    embed.add_field(name="🥇 Top Performers", value="\n".join(top) if top else "No attacks yet", inline=False)
    embed.add_field(name="⚔️ Attack Tracker", value="\n\n".join(tracker), inline=False)

    channel = bot.get_channel(WAR_CHANNEL_ID)
    if channel:
        mid = get_saved_message(WAR_MESSAGE_FILE)
        try:
            if mid:
                msg = await channel.fetch_message(mid)
                await msg.edit(embed=embed)
            else:
                msg = await channel.send(embed=embed)
                save_message(WAR_MESSAGE_FILE,msg.id)
        except:
            msg = await channel.send(embed=embed)
            save_message(WAR_MESSAGE_FILE,msg.id)

    # ---------------- Donation Leaderboard ----------------
    donations = {m["name"]:m["donations"] for m in members}
    last = load_json(LAST_DONATIONS_FILE)
    if donations!=last:
        await asyncio.to_thread(save_json,LAST_DONATIONS_FILE,donations)
        sorted_members = sorted(members,key=lambda x:x["donations"],reverse=True)
        leaderboard=[]
        for i,m in enumerate(sorted_members[:10]):
            medal = medals[i] if i<3 else "•"
            leaderboard.append(f"{medal} **{m['name']}** — {m['donations']}")
        embed = discord.Embed(title="🎁 Donation Leaderboard",description="\n".join(leaderboard),color=0xF1C40F)
        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if channel:
            mid = get_saved_message(LEADERBOARD_MESSAGE_FILE)
            try:
                if mid:
                    msg = await channel.fetch_message(mid)
                    await msg.edit(embed=embed)
                else:
                    msg = await channel.send(embed=embed)
                    save_message(LEADERBOARD_MESSAGE_FILE,msg.id)
            except:
                await channel.send(embed=embed)
                save_message(LEADERBOARD_MESSAGE_FILE,msg.id)

    # ---------------- War Ping Checker ----------------
    await check_war_pings(war)
    await check_unlinked_players(war)

# ---------------- Recruit Command ----------------
def generate_recruitment_image(clan):
    """Generate a recruitment image using only the banner, no badge."""
    try:
        max_width, max_height = 1000, 400
        banner = Image.open(BANNER_PATH).convert("RGBA")
        banner.thumbnail((max_width, max_height), Image.LANCZOS)
        banner_w, banner_h = banner.size

        canvas = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 255))
        banner_x = (max_width - banner_w) // 2
        banner_y = (max_height - banner_h) // 2
        canvas.paste(banner, (banner_x, banner_y))
        output = BytesIO()
        canvas.save(output, format="PNG")
        output.seek(0)
        return output

    except Exception as e:
        print(f"Error in generate_recruitment_image: {e}")
        fallback = Image.new("RGBA", (1000, 400), (0,0,0,255))
        out = BytesIO()
        fallback.save(out, format="PNG")
        out.seek(0)
        return out

@tree.command(name="recruit", description="Generate recruitment embed")
async def recruit(interaction: discord.Interaction):
    roles = [role.id for role in interaction.user.roles]
    if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.defer()

    encoded_tag = CLAN_TAG.replace("#", "%23")
    clan_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}"

    try:
        clan_data = await asyncio.to_thread(lambda: requests.get(clan_url, headers=headers, timeout=10).json())
    except Exception as e:
        await interaction.followup.send(f"Error fetching clan data: {e}")
        return

    if not clan_data or "name" not in clan_data:
        await interaction.followup.send("Error: Invalid clan data received.")
        return

    image = await asyncio.to_thread(lambda: generate_recruitment_image(clan_data))
    file = discord.File(fp=image, filename="recruit.png")

    embed = discord.Embed(
        title="Join AM Allegiance – AMA",
        description="⚔️ A relaxed farming clan with a competitive edge in wars and CWL! Whether you farm, donate, or attack, we have a place for you.",
        color=16753920
    )
    embed.set_image(url="attachment://recruit.png")
    embed.add_field(
        name="What We Offer",
        value="• Friendly, active community\n• War & CWL participation with automated attack reminders\n• Monthly leaderboards combining donations + war stars\n• Account linking with /link and /linked for personalized notifications",
        inline=False
    )
    embed.add_field(
        name="Clan Expectations",
        value="• Be respectful and stay active\n• Participate in war if opted in\n• Complete both attacks unless communicated otherwise\n• Link your Discord to your Clash account",
        inline=False
    )
    embed.add_field(
        name="Requirements",
        value="1️⃣ Be TH13+\n2️⃣ Ping leadership for an invite",
        inline=False
    )
    embed.add_field(
        name="AMA Bot Highlights",
        value="• Live war tracking for each member\n• Personalized pings for members who haven’t attacked\n• Auto-updating monthly leaderboard\n• Persistent data storage for continuity",
        inline=False
    )
    embed.set_footer(text="AM Allegiance • Clash of Clans")

    tag = clan_data.get("tag","")
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="View Clan",
        url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}"
    ))

    await interaction.followup.send(embed=embed, view=view, file=file)

# ---------------- Link / Linked Commands ----------------
async def safe_load_json(path): return await asyncio.to_thread(load_json,path)
async def safe_save_json(path,data): return await asyncio.to_thread(save_json,path,data)

@tree.command(name="link", description="Link your Clash player tag to your Discord")
@app_commands.describe(tag="Enter your Clash player tag (e.g., #ABCD123)")
async def link(interaction: discord.Interaction, tag: str):
    tag = tag.upper()
    if not TAG_REGEX.match(tag):
        await interaction.response.send_message(
            "❌ Invalid Clash tag! Include # and only use letters A-Z and numbers.", ephemeral=True
        )
        return

    linked = await safe_load_json(LINKED_FILE)
    user_id = str(interaction.user.id)
    if user_id not in linked:
        linked[user_id] = []

    if tag in linked[user_id]:
        await interaction.response.send_message(f"Already linked to {tag}", ephemeral=True)
        return

    linked[user_id].append(tag)
    await safe_save_json(LINKED_FILE, linked)
    await interaction.response.send_message(f"✅ Successfully linked your Discord to Clash tag {tag}", ephemeral=True)

@tree.command(name="linked", description="View linked Clash accounts")
@app_commands.describe(user="Optional: leaders can check another member")
async def linked(interaction: discord.Interaction, user: discord.Member | None = None):

    linked = await safe_load_json(LINKED_FILE)

    roles = [role.id for role in interaction.user.roles]
    is_leader = LEADER_ROLE_ID in roles or CO_LEADER_ROLE_ID in roles

    # If a leader specifies a user, check that user's links
    if user and is_leader:
        tags = linked.get(str(user.id), [])
        msg = f"{user.display_name}'s linked tags: {', '.join(tags) if tags else 'None'}"
        await interaction.response.send_message(msg, ephemeral=True)
        return

    # Otherwise show the user's own links
    user_id = str(interaction.user.id)
    tags = linked.get(user_id, [])

    await interaction.response.send_message(
        f"Your linked Clash tags: {', '.join(tags) if tags else 'None'}",
        ephemeral=True
    )

# ---------------- War Ping Helpers ----------------
async def ping_users_for_interval(interval, members):
    pings = load_json(WAR_PINGS_FILE)
    if interval not in pings:
        pings[interval] = []

    linked = load_json(LINKED_FILE)
    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    messages = []
    for m in members:
        name = m["name"]
        used_attacks = len(m.get("attacks", []))
        if interval != "end" and used_attacks > 0:
            continue

        for user_id, tags in linked.items():
            if any(tag.upper() == name.upper() for tag in tags):
                if user_id not in pings[interval]:
                    messages.append(f"<@{user_id}>")
                    pings[interval].append(user_id)

    if messages:
        await channel.send(f"⚠️ War Reminder ({interval}): {' '.join(messages)}")

    save_json(WAR_PINGS_FILE, pings)

async def check_war_pings(war):
    end_time = war.get("endTime")
    start_time = war.get("startTime")
    if not end_time:
        return

    now = datetime.now(timezone.utc)
    end_dt = datetime.strptime(end_time,"%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
    start_dt = datetime.strptime(start_time,"%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc) if start_time else None
    members = war.get("clan", {}).get("members", [])

    if start_dt and (now - start_dt) < timedelta(minutes=5):
        await ping_users_for_interval("start", members)

    if timedelta(hours=11, minutes=55) < (end_dt - now) < timedelta(hours=12):
        await ping_users_for_interval("12h", members)

    if timedelta(minutes=55) < (end_dt - now) < timedelta(hours=1):
        await ping_users_for_interval("1h", members)

    if (end_dt - now) < timedelta(minutes=5):
        await ping_users_for_interval("end", members)

async def check_unlinked_players(war):
    """Detect players in war who haven't linked their Discord."""

    members = war.get("clan", {}).get("members", [])
    linked = load_json(LINKED_FILE)
    warned = load_json(UNLINKED_WARN_FILE)

    channel = bot.get_channel(WAR_CHANNEL_ID)
    if not channel:
        return

    # Collect all linked tags
    linked_tags = set()
    for tags in linked.values():
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

    save_json(UNLINKED_WARN_FILE, warned)

# ---------------- Bot Ready ----------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await tree.sync()
    update_loop.start()

bot.run(DISCORD_TOKEN)