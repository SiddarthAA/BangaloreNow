#!/bin/bash
set -e

echo "Starting the event processing pipeline..."

# Source the .env file to load variables into the current shell session
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  set -a
  source .env
  set +a
else
  echo "Warning: .env file not found."
fi

# Your Python script now handles downloading, so we just need to run it.
# The GOOGLE_APPLICATION_CREDENTIALS variable is still required for the google-cloud-storage library to work.
echo "Executing base_filter.py to download and process events..."
python base_filter.py

echo "Python script finished. Loading database to Supabase..."

# This check will now pass because the .env file has been loaded into the shell.
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set."
    exit 1
fi

# pgloader can now access the DATABASE_URL from the environment.
pgloader load.load

echo "Database load complete. Pipeline finished successfully."
