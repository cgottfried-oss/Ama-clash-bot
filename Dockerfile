FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Upgrade pip, remove any preinstalled discord packages, install requirements
RUN pip install --upgrade pip && \
    pip uninstall -y discord py-cord && \
    pip install -r requirements.txt

# Debug step: verify discord.py is installed and where Python sees it
RUN pip show discord.py && python -c "import discord; print('discord.py file:', discord.__file__); print('discord.py version:', discord.__version__)"

# Copy bot code
COPY . .

# Start bot
CMD ["python", "bot_runner.py"]
