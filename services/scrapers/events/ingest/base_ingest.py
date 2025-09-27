import os 

import logging
class Logger:
    def __init__(self, name: str, level=logging.INFO):
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(name)

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
logger = Logger("blrnow : ingest")

import requests
import subprocess

from google.cloud import storage
from base_filter import filter_database

BUCKET_NAME = "blrnowbucket"
LATEST_FILE = "latest.txt"
EVENTS_DB = "events.db"
GITHUB_RELEASE_URL = "https://github.com/blr-today/dataset/releases/latest/download/events.db"

def get_latest_tag_from_github():
    try:
        r = requests.head(GITHUB_RELEASE_URL, allow_redirects=True)
        latest_tag = r.url.split("/")[-2]
        logger.info(f"Latest Release Tag In GitHub : {latest_tag}")

        return latest_tag
    
    except Exception as e:
        logger.error(f"Error Fetching GitHub Release : {e}")
        raise

def get_latest_tag_from_bucket():
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(LATEST_FILE)
    if blob.exists():
        latest = blob.download_as_text().strip()
        logger.info(f"Latest Release Tag In Bucket : {latest}")
        return latest
    
    logger.info("No Latest Release Tag Found In Bucket")
    return None

def update_bucket(latest_tag):
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    blob = bucket.blob(EVENTS_DB)
    blob.upload_from_filename(EVENTS_DB)
    logger.info(f"Uploaded {EVENTS_DB} to bucket {BUCKET_NAME}")

    blob = bucket.blob(LATEST_FILE)
    blob.upload_from_string(latest_tag)
    logger.info(f"Updated {LATEST_FILE} in bucket with {latest_tag}")

def main():
    logger.info("Starting BangaloreNow Ingest + Filter1")

    github_tag = get_latest_tag_from_github()
    bucket_tag = get_latest_tag_from_bucket()

    if github_tag == bucket_tag:
        logger.info("No New Release Found - Exiting")
        return False

    logger.info("Downloading Latest 'events.db' From GitHub")
    r = requests.get(GITHUB_RELEASE_URL, allow_redirects=True)
    with open(EVENTS_DB, "wb") as f:
        f.write(r.content)
    logger.info("Downloaded Latest 'events.db'")

    logger.info("Running base_filter.py ")
    filter_database()
    logger.info("base_filter.py Completed Successfully")

    update_bucket(github_tag)

    logger.info("Execution complete")
    return True

if __name__ == "__main__": 
    main()