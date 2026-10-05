import os
import json
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("TELEGRAM_TOKEN") #pulls your secret TELEGRAM_TOKEN and GEMINI_API_KEY from the server's environment variables. 
                                    #This is a security best practice so my passwords aren't exposed directly in the code.
API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN or not API_KEY: #safety check that crashes the bot immediately if the keys are missing, 
                             #rather than failing silently later.
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY environment variables!")

def load_courses(): #Opens and reads your seg_courses.json file into memory
                    #so the rest of the application can access it instantly.
    with open('seg_courses.json', 'r') as file:
        return json.load(file)

courses_data = load_courses()