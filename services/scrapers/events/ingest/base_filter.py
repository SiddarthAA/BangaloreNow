import json
import sqlite3
from datetime import datetime

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

def filter_database():
    db_path = 'events.db'
    try: 
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info("Connected Successfully To SQLite Database 'events.db'")

    except Exception as e: 
        logger.error("Failed To Connect To SQLite Database 'events.db'")

    cursor.execute('DROP TABLE IF EXISTS events_temp')
    cursor.execute('''
    CREATE TABLE events_temp (
        name TEXT,
        description TEXT,
        url TEXT,
        image TEXT,
        startDate TEXT,
        endDate TEXT,
        venue TEXT,
        address TEXT,
        lat TEXT,
        long TEXT,
        organizer TEXT
    )
    ''')
    cursor.execute("SELECT event_json FROM events")
    rows = cursor.fetchall()

    now = datetime.now()
    current_month = now.month
    current_year = now.year

    for row in rows:
        try:
            event_json = json.loads(row[0])
        except json.JSONDecodeError:
            continue

        startDate = event_json.get('startDate')
        if startDate:
            try:
                event_date_str = startDate.split('+')[0]
                event_date = datetime.fromisoformat(event_date_str)
                
                if event_date.year == current_year and event_date.month == current_month:
                    endDate = event_json.get('endDate')
                    if not endDate:
                        endDate = startDate

                    name = event_json.get('name')
                    description = event_json.get('description')
                    url = event_json.get('url')
                    image_data = event_json.get('image')
                    if isinstance(image_data, list):
                        if image_data:
                            image = image_data[0]
                        else:
                            image = None
                    else:
                        image = image_data

                    location = event_json.get('location', {})
                    venue = location.get('name') if isinstance(location, dict) else None
                    
                    address_parts = []
                    if isinstance(location, dict):
                        address_obj = location.get('address', {})
                        if isinstance(address_obj, dict):
                            address_parts.append(address_obj.get('streetAddress', ''))
                            address_parts.append(address_obj.get('addressLocality', ''))
                            address_parts.append(address_obj.get('addressRegion', ''))
                            address_parts.append(address_obj.get('postalCode', ''))
                            address_parts.append(address_obj.get('addressCountry', ''))
                        elif isinstance(address_obj, str):
                            address_parts.append(address_obj)
                    
                    address = ', '.join(filter(None, address_parts))


                    geo = location.get('geo', {}) if isinstance(location, dict) else {}
                    lat = geo.get('latitude') if isinstance(geo, dict) else None
                    long = geo.get('longitude') if isinstance(geo, dict) else None

                    organizer_obj = event_json.get('organizer', {})
                    organizer = organizer_obj.get('name') if isinstance(organizer_obj, dict) else None

                    cursor.execute('''
                    INSERT INTO events_temp (name, description, url, image, startDate, endDate, venue, address, lat, long, organizer)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, description, url, image, startDate, endDate, venue, address, lat, long, organizer))

            except (ValueError, TypeError) as e:
                logger.warning("Skipping Event Due To Data Error")
                continue
    cursor.execute('DROP TABLE events')
    cursor.execute('ALTER TABLE events_temp RENAME TO events')

    conn.commit()
    conn.close()
    logger.info("Closed Connection To SQLite Database 'events.db'")