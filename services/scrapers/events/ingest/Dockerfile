# Use official Python image (slim variant to keep image size small)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies if needed (e.g. curl, sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY base_ingest.py base_filter.py ./

# (Optional) Make scripts executable
RUN chmod +x base_ingest.py base_filter.py

# Default command: run your ingestion pipeline
CMD ["python", "base_ingest.py"]