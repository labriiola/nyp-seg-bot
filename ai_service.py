import json
import google.generativeai as genai
from config import API_KEY, courses_data

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-3.6-flash")

async def get_ai_response(user_text: str, context_prompt: str = "") -> str:
    prompt = f"""
    You are an official AI course advisor for Nanyang Polytechnic (NYP) School of Engineering (SEG).
    
    {context_prompt}

    Strict Boundaries:
    1. Answer the user's question clearly, warmly, and politely based on this SEG course dataset:
       {json.dumps(courses_data)}
    2. You ONLY answer questions related to NYP School of Engineering (SEG) diplomas, entry requirements, careers, and engineering/tech topics.
    3. If the user greets you (e.g., 'hello', 'hi'), greet them back warmly and briefly explain how you can help them with NYP SEG courses.
    4. If the user asks about non-SEG courses (e.g., Nursing, Business, Design, IT) or non-school topics, politely inform them that you are an NYP SEG Course Advisor and can only answer queries related to the School of Engineering.
    
    Official Webpage: https://www.nyp.edu.sg/schools/seg.html
    User Question: {user_text}
    """
    response = await model.generate_content_async(prompt)
    return response.text