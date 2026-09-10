import os
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Lightweight web server to satisfy Render's port binding health checks
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is live")

    def log_message(self, format, *args):
        return  # Suppress repetitive HTTP health check logs

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

# Fetch credentials securely from environment variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is missing in Render settings!")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is missing in Render settings!")

# Configure Gemini AI using gemini-1.5-flash-latest to resolve model resolution errors
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-latest")

def load_courses():
    with open('seg_courses.json', 'r') as file:
        return json.load(file)

courses_data = load_courses()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Browse SEG Diplomas", callback_data='browse_courses')],
        [InlineKeyboardButton("Check Cut-Off Points (COP)", callback_data='show_cop')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to the NYP SEG Course Advising Bot! Select an option below or type your question directly.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'browse_courses':
        keyboard = []
        for code, info in courses_data.items():
            keyboard.append([InlineKeyboardButton(f"{info['name']} ({code})", callback_data=f"diploma_{code}")])
        keyboard.append([InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a Diploma to view detailed information:", reply_markup=reply_markup)

    elif data.startswith('diploma_'):
        code = data.split('_')[1]
        info = courses_data.get(code)
        
        if info:
            text = (
                f"**{info['name']} ({code})**\n\n"
                f"**JAE COP Range:** {info['cop']} points\n"
                f"**Description:** {info['description']}\n\n"
                f"**Career Paths:** {', '.join(info['careers'])}"
            )
            
            keyboard = [
                [InlineKeyboardButton("Official NYP SEG Webpage", url="https://www.nyp.edu.sg/schools/seg.html")],
                [InlineKeyboardButton("« Back to Diplomas List", callback_data='browse_courses')],
                [InlineKeyboardButton("« Main Menu", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    elif data == 'show_cop':
        cop_list = "\n".join([f"• **{info['name']} ({code})**: {info['cop']} points" for code, info in courses_data.items()])
        keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"**NYP SEG Cut-Off Points (ELR2B2-C):**\n\n{cop_list}", reply_markup=reply_markup, parse_mode="Markdown")

    elif data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("Browse SEG Diplomas", callback_data='browse_courses')],
            [InlineKeyboardButton("Check Cut-Off Points (COP)", callback_data='show_cop')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Welcome to the NYP SEG Course Advising Bot! Select an option below or type your question directly.", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    # Persistent 'Back to Main Menu' button on all text responses
    keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Rule 1: Fast local response for website link requests
    if any(word in user_text.lower() for word in ["link", "webpage", "website"]):
        await update.message.reply_text(
            "Here is the official NYP School of Engineering website: https://www.nyp.edu.sg/schools/seg.html",
            reply_markup=reply_markup
        )
        return

    # Show typing status immediately to improve response feel
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Rule 2: Async LLM response generation with warm persona boundaries
    try:
        prompt = f"""
        You are an official AI course advisor for Nanyang Polytechnic (NYP) School of Engineering (SEG).
        
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
        await update.message.reply_text(response.text, reply_markup=reply_markup)
        
    except Exception as e:
        logging.error(f"LLM Error: {e}")
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            await update.message.reply_text(
                "🌸 I'm receiving a lot of questions right now! Please wait about 1 minute and try again.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "⚠️ Something went wrong on my end. Please try again in a moment.",
                reply_markup=reply_markup
            )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running with Gemini AI...")
    app.run_polling()