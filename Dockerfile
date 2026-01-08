# Use Python 3.12 Slim for efficiency
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for some compiled libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Set PYTHONPATH to include root
ENV PYTHONPATH=/app

# Command to run the bot
CMD ["python", "bot/bot_service.py"]
