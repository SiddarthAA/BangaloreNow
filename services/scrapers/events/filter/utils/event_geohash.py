import os
import requests

from dotenv import load_dotenv

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


class Geocoder:
    def __init__(self, api_key: str = None):
        try:
            load_dotenv()
            self.api_key = api_key or os.getenv("base_geo")
            if not self.api_key:
                logger.error("GeoHash API key not found in environment!")
            else:
                logger.info("GeoHash API key loaded successfully")
            
            self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        except Exception as e:
            logger.critical(f"Error initializing Geocoder: {e}")
            raise e

    def get_coordinates(self, address: str):
        """
        Returns latitude and longitude for a given address using Google Geocoding API.
        """
        try:
            params = {
                "address": address,
                "key": self.api_key
            }
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # raises HTTPError for bad status codes
            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                error_msg = data.get("error_message", "No results returned")
                logger.error(f"GeoHash API error: {data.get('status')} | {error_msg}")
                return None

            location = data["results"][0]["geometry"]["location"]
            lat, lng = location["lat"], location["lng"]
            logger.info(f"Generated Lat + Long for address '{address}': lat={lat}, lng={lng}")
            return [lat, lng]

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while geocoding address '{address}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while geocoding address '{address}': {e}")
            return None
