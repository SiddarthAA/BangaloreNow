# Stage 1: Builder
FROM python:3.11-slim as builder

# Install uv
RUN pip install uv

# Create a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# Stage 2: Final Image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pgloader \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy only the necessary application code
COPY base_filter.py .
COPY run.sh .
COPY utils/ ./utils/
COPY .env .
COPY load.load .

# Make the run script executable
RUN chmod +x run.sh

# Set the entrypoint to the run script
ENV PATH="/opt/venv/bin:$PATH"
ENTRYPOINT ["./run.sh"]
