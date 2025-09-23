from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import sqlite3
import gc
from utils.event_enhancer import EventEnhancer
# from utils.event_index import FaissIndexManager
from utils.event_geohash import Geocoder
from utils.event_fetch import download_events_db
import logging

class Logger:
    def __init__(self, name: str, level=logging.DEBUG):
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

def process_events(db_path: str = "events.db"):
    enhancer = EventEnhancer()
    # index_manager = FaissIndexManager()
    # index_manager.load_index()
    geocoder = Geocoder() # Instantiate Geocoder

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add uid column if it doesn't exist
        cursor.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]

        # Select all relevant fields, including address, lat, long and uid
        cursor.execute("SELECT rowid, name, description, address, lat, long, uid FROM events")
        
        batch_size = 25
        while True:
            events = cursor.fetchmany(batch_size)
            if not events:
                break

            to_delete = []
            to_update_description = []
            to_update_coordinates = []
            to_update_uid = []

            for rowid, name, description, address, lat, long, uid in events:
                logging.info(f"Processing event: {name}")

                # Check and update coordinates if missing
                if (not lat or not long or lat == "0.0" or long == "0.0") and address:
                    logging.info(f"Coordinates missing for '{name}'. Attempting to geocode address: '{address}'")
                    try:
                        new_lat, new_long = geocoder.get_coordinates(uid,address)
                        to_update_coordinates.append((str(new_lat), str(new_long), name))
                        logging.info(f"Successfully geocoded '{name}': Lat={new_lat}, Long={new_long}")
                    except ValueError as e:
                        logging.error(f"Failed to geocode address for '{name}': {e}")
                
                # Existing enhancement and indexing logic
                logging.debug(f"Original description: {description}")
                enhanced_description = enhancer.enhance_description(uid,description)
                logging.info(f"Enhanced description: {enhanced_description}")
                
                text_to_embed = f"{name}: {enhanced_description}"
                logging.debug(f"Text to embed: {text_to_embed}")

                # if index_manager.search(text_to_embed):
                #     to_delete.append(name)
                #     logging.info(f"Event '{name}' found in index. Marking for deletion.")
                # else:
                #     index_manager.add(text_to_embed)
                to_update_description.append((enhanced_description, name))
                logging.info(f"Event '{name}' not in index. Adding to index and marking for update.")

            if to_delete:
                cursor.executemany("DELETE FROM events WHERE name = ?", [(i,) for i in to_delete])
                logging.info(f"Deleted {len(to_delete)} events from the database.")

            if to_update_description:
                cursor.executemany("UPDATE events SET description = ? WHERE name = ?", to_update_description)
                logging.info(f"Updated {len(to_update_description)} event descriptions in the database.")
            
            if to_update_coordinates:
                cursor.executemany("UPDATE events SET lat = ?, long = ? WHERE name = ?", to_update_coordinates)
                logging.info(f"Updated {len(to_update_coordinates)} event coordinates in the database.")

            if to_update_uid:
                cursor.executemany("UPDATE events SET uid = ? WHERE rowid = ?", to_update_uid)
                logging.info(f"Updated {len(to_update_uid)} event uids in the database.")
            gc.collect()

        conn.commit()
        # index_manager.save_index()
        logging.info("Successfully processed all events, updated database, and saved index.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        conn.rollback()
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    download_events_db()
    process_events()