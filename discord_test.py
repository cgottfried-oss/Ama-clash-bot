# discord_test.py
import discord

print("--- DISCORD.PY TEST ---")
print("discord module path:", discord.__file__)
print("discord module dir:", dir(discord))
print("Bot exists:", hasattr(discord, "Bot"))

# Check version
try:
    import importlib.metadata as md
    print("discord.py version:", md.version("discord.py"))
except Exception as e:
    print("Could not detect discord.py version:", e)

print("--- END DISCORD.PY TEST ---")
