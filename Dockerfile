# Use Python 3.12 slim image
FROM python:3.12-slim

WORKDIR /app

# Copy requirements and bot code
COPY requirements.txt .
COPY . .

# Upgrade pip, uninstall any rogue discord packages, install requirements
RUN pip install --upgrade pip && \
    pip uninstall -y discord py-cord && \
    pip install -r requirements.txt

# Add a debug step to print discord info
RUN python -c "import discord; print('discord module path:', discord.__file__); print('discord module dir:', dir(discord))"

# Start bot and pause container so we can inspect
CMD ["sh", "-c", "python bot_runner.py || true && tail -f /dev/null"]
