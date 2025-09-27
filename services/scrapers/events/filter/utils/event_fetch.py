from google.cloud import storage

import logging
class Logger:
    def __init__(self, name: str, level=logging.INFO):
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
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
logger = Logger("blrnow : filter")


def download_events_db():
    """
    Downloads the latest events.db file from the Google Cloud Storage bucket.
    """
    bucket_name = "blrnowbucket"
    source_blob_name = "events.db"
    destination_file_name = "/tmp/events.db"

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)

        blob.download_to_filename(destination_file_name)
        logger.info(f"Successfully downloaded '{source_blob_name}' from bucket '{bucket_name}'")

    except Exception as e:
        logger.error(f"Failed to download '{source_blob_name}' from bucket '{bucket_name}': {e}")
        raise e  # re-raise so the caller knows the download failed
    