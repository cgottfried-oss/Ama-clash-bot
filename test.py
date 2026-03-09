import discord
from discord.ext import commands, tasks
from discord import app_commands

print("discord module version:", discord.__version__)

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

# Don't actually run the bot, just verify imports
print("Imports work! app_commands is available.")