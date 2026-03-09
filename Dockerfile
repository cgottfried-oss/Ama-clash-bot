# Use Python 3.12 slim image
FROM python:3.12-slim

WORKDIR /app
# Debug step: run test script
RUN python discord_test.py
# Copy requirements and bot code
COPY requirements.txt .
COPY . .

# Upgrade pip, uninstall any rogue discord packages, install requirements
RUN pip install --upgrade pip && \
    pip uninstall -y discord py-cord && \
    pip install -r requirements.txt

# Debug step: print discord.py info
RUN python -c "\
import discord; \
print('--- DISCORD.PY DEBUG ---'); \
print('discord module path:', discord.__file__); \
print('discord module dir:', dir(discord)); \
print('Bot exists:', hasattr(discord, 'Bot')); \
try: \
    import importlib.metadata as md; \
    print('discord.py version:', md.version('discord.py')); \
except: \
    print('Could not detect discord.py version'); \
print('--- END DEBUG ---')"

# Start bot normally (tail -f keeps container alive if bot fails)
CMD ["sh", "-c", "python bot_runner.py || true && tail -f /dev/null"]
