import os
import json
import requests
from datetime import datetime, timezone
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

WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
LEADERBOARD_MESSAGE_FILE = os.path.join(DATA_DIR, "leaderboard_message_id.txt")
LAST_DONATIONS_FILE = os.path.join(DATA_DIR, "last_donations.json")
CWL_FILE = os.path.join(DATA_DIR, "cwl_data.json")
MISSED_FILE = os.path.join(DATA_DIR, "missed_attacks.json")
MVP_FILE = os.path.join(DATA_DIR, "mvp_data.json")
ASSIGN_FILE = os.path.join(DATA_DIR, "war_assignments.json")
LINKED_FILE = os.path.join(DATA_DIR, "linked_players.json")
TAG_REGEX = re.compile(r"^#[A-Z0-9]{3,12}$"

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
                msg = await channel.send(embed=embed)
                save_message(LEADERBOARD_MESSAGE_FILE,msg.id)

# ---------------- Recruit Command ----------------
def generate_recruitment_image(clan):
    """Generate a recruitment image using only the banner, no badge."""
    try:
        # ---------------- Banner ----------------
        max_width, max_height = 1000, 400
        banner = Image.open(BANNER_PATH).convert("RGBA")
        banner.thumbnail((max_width, max_height), Image.LANCZOS)
        banner_w, banner_h = banner.size

        # Center banner on black canvas (1000x400)
        canvas = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 255))
        banner_x = (max_width - banner_w) // 2
        banner_y = (max_height - banner_h) // 2
        canvas.paste(banner, (banner_x, banner_y))
        return_bytes = BytesIO()
        canvas.save(return_bytes, format="PNG")
        return_bytes.seek(0)
        return return_bytes

    except Exception as e:
        print(f"Error in generate_recruitment_image: {e}")
        fallback = Image.new("RGBA", (1000, 400), (0, 0, 0, 255))
        output = BytesIO()
        fallback.save(output, format="PNG")
        output.seek(0)
        return output


@tree.command(name="recruit", description="Generate recruitment embed")
async def recruit(interaction: discord.Interaction):
    roles = [role.id for role in interaction.user.roles]
    if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.defer()

    encoded_tag = CLAN_TAG.replace("#", "%23")
    clan_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}"

    # Fetch clan data
    try:
        clan_data = await asyncio.to_thread(lambda: requests.get(clan_url, headers=headers, timeout=10).json())
    except Exception as e:
        await interaction.followup.send(f"Error fetching clan data: {e}")
        return

    if not clan_data or "name" not in clan_data:
        await interaction.followup.send("Error: Invalid clan data received.")
        return

    # Generate banner image
    image = await asyncio.to_thread(lambda: generate_recruitment_image(clan_data))
    file = discord.File(fp=image, filename="recruit.png")

    # Construct embed with requested fields
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
    # ---------------- New field for TH13 requirement ----------------
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

    # Add button to view clan
    tag = clan_data.get("tag", "")
    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="View Clan",
            url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}"
        )
    )

    await interaction.followup.send(embed=embed, view=view, file=file)

# ---------------- CWL / Bonus / MVP / Assign / Link Commands ----------------
async def safe_load_json(path): return await asyncio.to_thread(load_json,path)
async def safe_save_json(path,data): return await asyncio.to_thread(save_json,path,data)

# (Other commands stay unchanged...)

# ---------------- Bot Ready ----------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await tree.sync()
    update_loop.start()

bot.run(DISCORD_TOKEN)
