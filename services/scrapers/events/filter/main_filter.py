import sqlite3
from utils.event_postgres import push_events_to_supabase
from utils.event_fetch import download_events_db
from utils.event_enhancer import EventEnhancer
from utils.event_geohash import Geocoder
    
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


def process_events():
    logger.info("Starting event processing...")

    # Step 1: Download the latest events.db
    try:
        download_events_db()
        logger.info("Downloaded events.db successfully.")
    except Exception as e:
        logger.error(f"Error downloading events.db: {e}")
        return
    

    enhancer = EventEnhancer()
    geocoder = Geocoder()

    try:
        conn = sqlite3.connect('/tmp/events.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        update_cursor = conn.cursor()
        logger.info("Connected to SQLite database.")

        cursor.execute("SELECT * FROM events")
        total_events = 0
        while True:
            event = cursor.fetchone()
            if event is None:
                break

            total_events += 1
            event_dict = dict(event)
            description = event_dict.get("description")
            lat = event_dict.get("lat")
            long = event_dict.get("long")
            address = event_dict.get("address")

            # Enhance description
            if description:
                try:
                    enhanced_description = enhancer.enhance_description(description)
                except Exception as e:
                    logger.error(f"Error enhancing description for event '{event_dict.get('name')}': {e}")
                    enhanced_description = description
            else:
                enhanced_description = description

            # Geocode if lat/long missing
            if (lat is None or long is None) and address:
                try:
                    coords = geocoder.get_coordinates(address)
                    if coords:
                        lat, long = coords
                except Exception as e:
                    logger.warning(f"Error geocoding address '{address}' for event '{event_dict.get('name')}': {e}")

            # Update SQLite table
            try:
                update_cursor.execute("""
                    UPDATE events
                    SET description = ?, lat = ?, long = ?
                    WHERE name = ?
                """, (enhanced_description, lat, long, event_dict["name"]))
            except Exception as e:
                logger.error(f"Error updating event '{event_dict.get('name')}': {e}")

            if total_events % 50 == 0:
                logger.info(f"Processed {total_events} events so far...")

        conn.commit()
        logger.info(f"Finished processing {total_events} events. All changes committed.")

    except Exception as e:
        logger.error(f"Error during SQLite processing: {e}")

    finally:
        conn.close()
        logger.info("Closed SQLite connection.")

if __name__ == "__main__":
    logger.info("==== BlrNow - Filter Script Started ====")
    
    try:
        process_events()
        logger.info("Event processing completed successfully.")
    except Exception as e:
        logger.error(f"Unexpected error during event processing: {e}")

    logger.info("Starting migration of events to PostgreSQL...")
    try:
        push_events_to_supabase()
        logger.info("Migration to PostgreSQL completed successfully.")
    except Exception as e:
        logger.error(f"Error during PostgreSQL migration: {e}")
    
    logger.info("==== BlrNow - Filter Script Finished ====")