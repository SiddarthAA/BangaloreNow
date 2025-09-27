import os
from google import genai
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


class EventEnhancer:
    def __init__(self, api_key_env: str = "base_gemini"):
        try:
            load_dotenv()
            api_key = os.getenv(api_key_env)
            if not api_key:
                logger.error(f"Enhancer API key not found in environment variable '{api_key_env}'")
            else:
                logger.info("Enhancer API key loaded successfully")
            
            self.client = genai.Client(api_key=api_key)
            logger.info("GenAI client initialized successfully")
        except Exception as e:
            logger.critical(f"Error initializing EventEnhancer: {e}")
            raise e  # Re-raise so that user knows initialization failed

    def enhance_description(self, description: str) -> str:
        try:
            prompt = (
                "You are an AI that only returns a concise, enriched event description. "
                "Output exactly 30–50 words that cover the core of the event. "
                "Do not include any explanations, instructions, labels, or extra text.\n"
                f"Event Description: {description}"
            )

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )

            enhanced = response.text.strip()
            logger.info(f"Generated enhanced description for event: {enhanced[:60]}{'...' if len(enhanced) > 60 else ''}")
            return enhanced

        except Exception as e:
            logger.error(f"Error generating enhanced description: {e}")
            return description  # fallback to original description