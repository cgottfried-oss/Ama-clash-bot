FROM python:3.11-slim

WORKDIR /app

# Install minimal deps (fonts for Pillow text rendering)
RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot_runner.py"]
