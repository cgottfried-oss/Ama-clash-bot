import discord
from discord.ext import commands, tasks
import requests
import json
import os
import time

# -------------------------
# Persistent storage setup
# -------------------------
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

PLAYER_LINK_FILE = os.path.join(DATA_DIR, "player_links.json")
WAR_MESSAGE_FILE = os.path.join(DATA_DIR, "war_message_id.txt")
WAR_ALERT_FILE = os.path.join(DATA_DIR, "war_alerts_log.txt")

# -------------------------
# Safe env variable loader
# -------------------------
def get_env_var(name):
    val = os.environ.get(name)
    if not val:
        raise ValueError(f"⚠️ Environment variable {name} not set!")
    return val

def get_int_env(name):
    val = os.environ.get(name)
    if not val:
        raise ValueError(f"⚠️ Environment variable {name} not set!")
    return int(val)

# Load environment at runtime
DISCORD_TOKEN = get_env_var("DISCORD_TOKEN")
API_KEY = get_env_var("CLASH_API_KEY")
CLAN_TAG = get_env_var("CLAN_TAG")
WAR_CHANNEL_ID = get_int_env("WAR_CHANNEL_ID")
WAR_ROLE_ID = get_int_env("WAR_ROLE_ID")

# -------------------------
# Discord bot setup
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# Player link helpers
# -------------------------
def load_player_links():
    if os.path.exists(PLAYER_LINK_FILE):
        with open(PLAYER_LINK_FILE) as f:
            return json.load(f)
    return {}

def save_player_links(data):
    with open(PLAYER_LINK_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.command()
async def link(ctx, *, player_name):
    links = load_player_links()
    links[player_name] = str(ctx.author.id)
    save_player_links(links)
    await ctx.send(f"✅ **{player_name}** is now linked to {ctx.author.mention}")

# -------------------------
# War message ID helpers
# -------------------------
def get_saved_war_message_id():
    if os.path.exists(WAR_MESSAGE_FILE):
        with open(WAR_MESSAGE_FILE) as f:
            return f.read().strip()
    return None

def save_war_message_id(msg_id):
    with open(WAR_MESSAGE_FILE, "w") as f:
        f.write(str(msg_id))

# -------------------------
# War alerts log helpers
# -------------------------
def has_alert_fired(alert_name):
    if not os.path.exists(WAR_ALERT_FILE):
        return False
    with open(WAR_ALERT_FILE) as f:
        return alert_name in f.read().splitlines()

def log_alert(alert_name):
    with open(WAR_ALERT_FILE, "a") as f:
        f.write(alert_name + "\n")

# -------------------------
# Fetch current war data
# -------------------------
headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
encoded_clan_tag = CLAN_TAG.replace("#", "%23")
war_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"

def fetch_war():
    try:
        r = requests.get(war_url, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print("❌ Error fetching war data:", e)
        return None

# -------------------------
# Build war embed
# -------------------------
def build_war_embed(data):
    clan_name = data["clan"]["name"]
    opponent_name = data["opponent"]["name"]
    team_size = data["teamSize"]
    state = data["state"]

    embed = discord.Embed(
        title=f"⚔️ {clan_name} vs {opponent_name}",
        description=f"War State: **{state.upper()}**",
        color=discord.Color.green() if data["clan"]["stars"] >= data["opponent"]["stars"] else discord.Color.red()
    )

    members = data["clan"]["members"]
    lines = []
    missing_attacks = []
    attacks_per_member = data.get("attacksPerMember", 2)
    player_links = load_player_links()

    for m in members:
        name = m["name"]
        attacks = m.get("attacks", [])
        attack_count = len(attacks)
        stars = sum(a.get("stars", 0) for a in attacks) if attacks else 0

        if attack_count >= attacks_per_member:
            status = "🟢"
        elif attack_count == 1:
            status = "🟡"
            missing_attacks.append(name)
        else:
            status = "🔴"
            missing_attacks.append(name)

        lines.append(f"{status} {name} • {attack_count}/{attacks_per_member} • {stars}⭐")

    embed.add_field(name="⚔️ Attack Status", value="\n".join(lines), inline=False)
    return embed, missing_attacks

# -------------------------
# War monitoring loop
# -------------------------
START_TIME = time.time()

@tasks.loop(minutes=5)
async def war_loop():
    data = fetch_war()
    if not data:
        return

    channel = bot.get_channel(WAR_CHANNEL_ID)
    embed, missing = build_war_embed(data)

    # Edit existing embed or send new
    message_id = get_saved_war_message_id()
    try:
        if message_id:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            save_war_message_id(msg.id)
    except discord.NotFound:
        msg = await channel.send(embed=embed)
        save_war_message_id(msg.id)

    # Missing attack pings (once per war)
    if missing and (time.time() - START_TIME) > 300 and not has_alert_fired("missing_attacks"):
        player_links = load_player_links()
        missing_pings = []
        for name in missing:
            if name in player_links:
                missing_pings.append(f"<@{player_links[name]}>")
            else:
                missing_pings.append(name)
        msg_text = "🚨 **War attacks remaining!**\n\n" + "\n".join(missing_pings)
        await channel.send(msg_text)
        log_alert("missing_attacks")

    # War ended alert
    if data["state"] == "warEnded" and not has_alert_fired("war_end"):
        await channel.send(f"🏁 <@&{WAR_ROLE_ID}> **War has ended!**")
        log_alert("war_end")

# -------------------------
# Bot ready
# -------------------------
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    war_loop.start()

bot.run(DISCORD_TOKEN)