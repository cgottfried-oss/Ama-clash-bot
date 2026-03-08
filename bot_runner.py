import discord
from discord.ext import commands, tasks
import requests
import json
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("CLASH_API_KEY")
CLAN_TAG = os.getenv("CLAN_TAG")

WAR_CHANNEL_ID = int(os.getenv("WAR_CHANNEL_ID"))
WAR_ROLE_ID = int(os.getenv("WAR_ROLE_ID"))

PLAYER_LINK_FILE = "player_links.json"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

encoded_clan_tag = CLAN_TAG.replace("#", "%23")
war_url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}/currentwar"


# -------------------------
# Player Link System
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
# War Data Fetch
# -------------------------

def fetch_war():

    r = requests.get(war_url, headers=headers)

    if r.status_code != 200:
        print("Error fetching war data:", r.text)
        return None

    return r.json()


# -------------------------
# Build War Embed
# -------------------------

def build_war_embed(data):

    clan = data["clan"]["name"]
    opponent = data["opponent"]["name"]

    team_size = data["teamSize"]
    state = data["state"]

    embed = discord.Embed(
        title=f"{clan} vs {opponent}",
        description=f"War State: **{state.upper()}**",
        color=discord.Color.red()
    )

    members = data["clan"]["members"]

    lines = []

    for m in members:

        name = m["name"]

        attacks = m.get("attacks", [])

        attack_count = len(attacks)

        if attack_count == 2:
            status = "🟢 2/2"
        elif attack_count == 1:
            status = "🟡 1/2"
        else:
            status = "🔴 0/2"

        stars = sum(a["stars"] for a in attacks) if attacks else 0

        lines.append(f"{status} **{name}** ⭐{stars}")

    embed.add_field(
        name="War Attacks",
        value="\n".join(lines),
        inline=False
    )

    return embed


# -------------------------
# Missing Attack Detection
# -------------------------

def find_missing_attacks(data):

    members = data["clan"]["members"]

    links = load_player_links()

    missing = []

    for m in members:

        name = m["name"]

        attacks = m.get("attacks", [])

        if len(attacks) < 2:

            if name in links:

                discord_id = links[name]

                missing.append(f"<@{discord_id}>")

            else:

                missing.append(name)

    return missing


# -------------------------
# War Monitoring Loop
# -------------------------

last_ping_state = None


@tasks.loop(minutes=5)
async def war_loop():

    global last_ping_state

    data = fetch_war()

    if not data:
        return

    channel = bot.get_channel(WAR_CHANNEL_ID)

    embed = build_war_embed(data)

    await channel.send(embed=embed)

    state = data["state"]

    if state == "inWar":

        missing = find_missing_attacks(data)

        if missing and last_ping_state != "missing":

            msg = (
                "🚨 **War attacks remaining!**\n\n"
                + "\n".join(missing)
            )

            await channel.send(msg)

            last_ping_state = "missing"

    if state == "warEnded":

        last_ping_state = "ended"

        role = f"<@&{WAR_ROLE_ID}>"

        await channel.send(f"🏁 {role} **War has ended!**")


# -------------------------
# Bot Ready
# -------------------------

@bot.event
async def on_ready():

    print(f"Bot logged in as {bot.user}")

    war_loop.start()


bot.run(DISCORD_TOKEN)