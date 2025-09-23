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
logger = Logger("blrnow : desc-enhancer")

class EventEnhancer:
    def __init__(self, api_key_env: str = "base_gemini"):
        load_dotenv()
        api_key = os.getenv(api_key_env)
        if not api_key:
            logger.error(f"Enhancer API key not found in environment!") #log file
        
        self.client = genai.Client(api_key=api_key)

    def enhance_description(self, description: str) -> str:
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

        logger.info("Generated Enhanced Description For Event") #log file
        return response.text.strip()