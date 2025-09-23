import os
import requests
from dotenv import load_dotenv
load_dotenv()

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
logger = Logger("blrnow : geo-hash")

class Geocoder:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("base_geo")
        if not self.api_key:
            logger.error("GeoHash API key not found in environment!") #log file

        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def get_coordinates(self, address: str):
        params = {
            "address": address,
            "key": self.api_key
        }
        response = requests.get(self.base_url, params=params)
        data = response.json()

        if data.get("status") != "OK":
            logger.error(f"GeoHash API error: {data.get('status')} | {data.get('error_message')}")

        location = data["results"][0]["geometry"]["location"]
        logger.info("Generated Lat + Long For Event") #log file
        return [location["lat"], location["lng"]]