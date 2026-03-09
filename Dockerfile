FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Upgrade pip and remove any preinstalled discord package
RUN pip install --upgrade pip && \
    pip uninstall -y discord py-cord && \
    pip install -r requirements.txt

# Copy bot code
COPY . .

# Start bot
CMD ["python", "bot_runner.py"]
