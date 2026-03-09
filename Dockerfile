# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Upgrade pip, remove any preinstalled Discord libraries, install requirements, and check version
RUN pip install --upgrade pip && \
    pip uninstall -y discord py-cord && \
    pip install -r requirements.txt && \
    echo "Installed packages:" && \
    pip list && \
    echo "Checking discord.py version:" && \
    pip show discord.py

# Copy bot code
COPY . .

# Debug: run a small Python command to show discord attributes
RUN python -c "import discord; print('discord module path:', discord.__file__); print('discord module dir:', dir(discord))"

# Start bot
CMD ["python", "bot_runner.py"]
