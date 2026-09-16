import os
import json
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN or not API_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY environment variables!")

def load_courses():
    with open('seg_courses.json', 'r') as file:
        return json.load(file)

courses_data = load_courses()