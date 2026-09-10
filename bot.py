import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# --- 1. Start Dummy Web Server for Render Health Checks ---
def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

# Run HTTP server in background thread so Telegram bot runs concurrently
threading.Thread(target=run_health_check_server, daemon=True).start()

# --- 2. Configure Gemini AI ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# --- 3. Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your SEG Course Advising Bot. How can I help you today?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        # Generate response from Gemini AI
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)

    except Exception as e:
        error_str = str(e)
        # Catch rate limits (429) or quota exhaustion politely
        if "429" in error_str or "quota" in error_str.lower():
            await update.message.reply_text(
                "🌸 I'm receiving a lot of questions right now! Please wait about 1 minute and try again."
            )
        else:
            await update.message.reply_text(
                "⚠️ Something went wrong on my end. Please try again in a moment."
            )

# --- 4. Main Execution ---
if __name__ == "__main__":
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is starting...")
    app.run_polling()