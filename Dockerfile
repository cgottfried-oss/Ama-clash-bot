# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install packages
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the bot code
COPY . .

# Start the bot
CMD ["python", "bot_runner.py"]
