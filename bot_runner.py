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
WARNED_FILE = os.path.join(DATA_DIR, "warned_players.json")

CWL_FILE = os.path.join(DATA_DIR, "cwl_data.json")
MISSED_FILE = os.path.join(DATA_DIR, "missed_attacks.json")
MVP_FILE = os.path.join(DATA_DIR, "mvp_data.json")
ASSIGN_FILE = os.path.join(DATA_DIR, "war_assignments.json")

headers = {
    "Authorization": f"Bearer {CLASH_API_KEY}",
    "Accept": "application/json"
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree


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


def update_cwl_stats(members):

    cwl = load_json(CWL_FILE)

    for m in members:

        name = m["name"]

        attacks = m.get("attacks", [])

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        if name not in cwl:
            cwl[name] = {
                "stars": 0,
                "destruction": 0,
                "attacks": 0
            }

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

        stars = sum(a.get("stars", 0) for a in m.get("attacks", []))

        donations = m.get("donations", 0)

        if name not in mvp:
            mvp[name] = {
                "stars": 0,
                "donations": 0,
                "attacks": 0
            }

        mvp[name]["stars"] += stars
        mvp[name]["donations"] += donations
        mvp[name]["attacks"] += len(m.get("attacks", []))

    save_json(MVP_FILE, mvp)


@tasks.loop(minutes=5)
async def update_loop():

    encoded_tag = CLAN_TAG.replace("#", "%23")

    war_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/currentwar"
    members_url = f"https://api.clashofclans.com/v1/clans/{encoded_tag}/members"

    try:
        war = requests.get(war_url, headers=headers).json()
        members = requests.get(members_url, headers=headers).json()["items"]
    except:
        print("API error")
        return

    clan = war.get("clan", {})
    opponent = war.get("opponent", {})

    state = war.get("state", "N/A")
    team_size = war.get("teamSize", 0)
    attacks_per_member = war.get("attacksPerMember", 2)

    update_cwl_stats(clan.get("members", []))
    track_missed_attacks(clan.get("members", []), attacks_per_member)
    update_mvp(clan.get("members", []))

    end_time = war.get("endTime")

    if end_time:
        end_dt = datetime.strptime(end_time, "%Y%m%dT%H%M%S.000Z").replace(tzinfo=timezone.utc)
        time_remaining = str(end_dt - datetime.now(timezone.utc)).split(".")[0]
    else:
        time_remaining = "N/A"

    members_data = []

    total_attacks = 0

    for m in clan.get("members", []):

        attacks = m.get("attacks", [])

        stars = sum(a.get("stars", 0) for a in attacks)
        destruction = sum(a.get("destructionPercentage", 0) for a in attacks)

        total_attacks += len(attacks)

        members_data.append({
            "name": m["name"],
            "attacks": len(attacks),
            "stars": stars,
            "destruction": destruction
        })

    members_data.sort(key=lambda x: (x["stars"], x["destruction"]), reverse=True)

    medals = ["🥇", "🥈", "🥉"]

    top = []
    tracker = []

    for i, m in enumerate(members_data):

        if i < 3 and m["stars"] > 0:
            top.append(f"{medals[i]} **{m['name']}**")

        warn = " ⚠️" if m["attacks"] == 0 else ""

        tracker.append(
            f"**{m['name']}**\n➤ {m['attacks']}/{attacks_per_member} • {m['stars']}⭐ • {m['destruction']}%{warn}"
        )

    embed = discord.Embed(
        title=f"⚔️ {clan.get('name')} vs {opponent.get('name','Opponent')}",
        description=(
            f"State: **{state}**\n"
            f"Team Size: **{team_size}v{team_size}**\n"
            f"Time Remaining: **{time_remaining}**\n\n"
            f"🔥 Attacks Used: **{total_attacks}/{team_size*attacks_per_member}**\n"
            f"⭐ Score: **{clan.get('stars',0)} — {opponent.get('stars',0)}**"
        ),
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
                save_message(WAR_MESSAGE_FILE, msg.id)

        except:

            msg = await channel.send(embed=embed)
            save_message(WAR_MESSAGE_FILE, msg.id)

    donations = {m["name"]: m["donations"] for m in members}

    last = load_json(LAST_DONATIONS_FILE)

    if donations != last:

        save_json(LAST_DONATIONS_FILE, donations)

        sorted_members = sorted(members, key=lambda x: x["donations"], reverse=True)

        leaderboard = []

        medals = ["🥇", "🥈", "🥉"]

        for i, m in enumerate(sorted_members[:10]):

            medal = medals[i] if i < 3 else "•"

            leaderboard.append(f"{medal} **{m['name']}** — {m['donations']}")

        embed = discord.Embed(
            title="🎁 Donation Leaderboard",
            description="\n".join(leaderboard),
            color=0xF1C40F
        )

        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)

        if channel:

            mid = get_saved_message(LEADERBOARD_MESSAGE_FILE)

            try:

                if mid:

                    msg = await channel.fetch_message(mid)
                    await msg.edit(embed=embed)

                else:

                    msg = await channel.send(embed=embed)
                    save_message(LEADERBOARD_MESSAGE_FILE, msg.id)

            except:

                msg = await channel.send(embed=embed)
                save_message(LEADERBOARD_MESSAGE_FILE, msg.id)


@tree.command(name="cwl", description="CWL leaderboard")
async def cwl(interaction: discord.Interaction):

    cwl = load_json(CWL_FILE)

    sorted_players = sorted(
        cwl.items(),
        key=lambda x: (x[1]["stars"], x[1]["destruction"]),
        reverse=True
    )

    lines = []

    medals = ["🥇", "🥈", "🥉"]

    for i, (name, data) in enumerate(sorted_players[:10]):

        medal = medals[i] if i < 3 else "•"

        lines.append(f"{medal} {name} — {data['stars']}⭐")

    embed = discord.Embed(
        title="🏆 CWL Leaderboard",
        description="\n".join(lines),
        color=0x9B59B6
    )

    await interaction.response.send_message(embed=embed)


@tree.command(name="bonus", description="Suggest CWL bonus medal winners")
async def bonus(interaction: discord.Interaction):

    cwl = load_json(CWL_FILE)

    sorted_players = sorted(
        cwl.items(),
        key=lambda x: x[1]["stars"],
        reverse=True
    )

    lines = []

    for name, data in sorted_players[:5]:
        lines.append(f"⭐ {name} — {data['stars']}")

    embed = discord.Embed(
        title="🏅 Suggested Bonus Medal Winners",
        description="\n".join(lines),
        color=0xF39C12
    )

    await interaction.response.send_message(embed=embed)


@tree.command(name="mvp", description="Monthly clan MVP leaderboard")
async def mvp(interaction: discord.Interaction):

    mvp = load_json(MVP_FILE)

    sorted_players = sorted(
        mvp.items(),
        key=lambda x: (x[1]["stars"] + x[1]["donations"]/100),
        reverse=True
    )

    lines = []

    medals = ["🥇", "🥈", "🥉"]

    for i, (name, data) in enumerate(sorted_players[:10]):

        medal = medals[i] if i < 3 else "•"

        lines.append(
            f"{medal} {name} — {data['stars']}⭐ | {data['donations']} donations"
        )

    embed = discord.Embed(
        title="🏆 Monthly Clan MVP",
        description="\n".join(lines),
        color=0xE74C3C
    )

    await interaction.response.send_message(embed=embed)


@tree.command(name="assign", description="Assign war target")
@app_commands.describe(player="Player name", target="Enemy base number")
async def assign(interaction: discord.Interaction, player: str, target: int):

    roles = [r.id for r in interaction.user.roles]

    if LEADER_ROLE_ID not in roles and CO_LEADER_ROLE_ID not in roles:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    assigns = load_json(ASSIGN_FILE)

    assigns[player] = target

    save_json(ASSIGN_FILE, assigns)

    await interaction.response.send_message(f"Assigned **{player}** → Base **{target}**")


@tree.command(name="assignments", description="View war assignments")
async def assignments(interaction: discord.Interaction):

    assigns = load_json(ASSIGN_FILE)

    if not assigns:
        await interaction.response.send_message("No assignments yet.")
        return

    lines = []

    for player, target in assigns.items():
        lines.append(f"⚔️ {player} → Base {target}")

    embed = discord.Embed(
        title="War Assignments",
        description="\n".join(lines),
        color=0x3498DB
    )

    await interaction.response.send_message(embed=embed)
    
def download_assets():

    banner_url = "https://i.imgur.com/vNTiwib.png"
    logo_url = "https://i.imgur.com/jXnZ622.png"

    if not os.path.exists(BANNER_PATH):
        print("Downloading clan banner...")
        r = requests.get(banner_url, timeout=10)
        with open(BANNER_PATH, "wb") as f:
            f.write(r.content)

    if not os.path.exists(LOGO_PATH):
        print("Downloading clan logo...")
        r = requests.get(logo_url, timeout=10)
        with open(LOGO_PATH, "wb") as f:
            f.write(r.content)

def generate_recruitment_image(clan):

    banner = Image.open(BANNER_PATH).convert("RGBA")
    banner = banner.resize((1000, 400))

    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((160, 160))

    draw = ImageDraw.Draw(banner)

    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 60)
        stat_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        recruit_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
    except:
        title_font = ImageFont.load_default()
        stat_font = ImageFont.load_default()
        recruit_font = ImageFont.load_default()

    name = clan.get("name")
    level = clan.get("clanLevel")
    members = clan.get("members")
    league = clan.get("warLeague", {}).get("name")

    # Clan title
    draw.text((220, 40), name, font=title_font, fill=(255,255,255))

    # Clan stats
    stats = [
        f"Clan Level: {level}",
        f"CWL League: {league}",
        f"Members: {members}/50"
    ]

    y = 140
    for stat in stats:
        draw.text((220, y), stat, font=stat_font, fill=(255,255,255))
        y += 50

    # Recruiting badge
    badge_text = "RECRUITING: TH13+"

    bbox = draw.textbbox((0,0), badge_text, font=recruit_font)
    badge_w = bbox[2] - bbox[0]
    badge_h = bbox[3] - bbox[1]

    badge_x = 650
    badge_y = 300

    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w + 40, badge_y + badge_h + 20],
        radius=15,
        fill=(0,0,0,160)
    )

    draw.text(
        (badge_x + 20, badge_y + 10),
        badge_text,
        font=recruit_font,
        fill=(255,215,0)
    )

    banner.paste(logo, (40,120), logo)

    output = BytesIO()
    banner.save(output, format="PNG")
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

    clan = requests.get(clan_url, headers=headers).json()

    tag = clan.get("tag")

    embed = discord.Embed(
        title="⚔️ AM Allegiance – Rise With Us",
        description="A clan built on loyalty, activity, and smart wars.",
        color=0xFFA500
    )

    embed.set_thumbnail(url="https://i.imgur.com/jXnZ622.png")

    image = generate_recruitment_image(clan)

    file = discord.File(fp=image, filename="recruit.png")

    embed.set_image(url="attachment://recruit.png")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="View Clan",
            url=f"https://link.clashofclans.com/en?action=OpenClanProfile&tag={tag.replace('#','%23')}"
        )
    )

    await interaction.followup.send(embed=embed, view=view, file=file)

@bot.event
async def on_ready():

    print(f"Bot logged in as {bot.user}")

    download_assets()

    await tree.sync()

    update_loop.start()


bot.run(DISCORD_TOKEN)