import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import courses_data
from ai_service import get_ai_response

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command. Resets stored user memory and presents the main menu.
    """
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("Browse SEG Diplomas 🎓", callback_data='browse_courses')],
        [InlineKeyboardButton("Check Cut-Off Points (COP) 📊", callback_data='show_cop')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to the NYP SEG Course Advising Bot! Select an option below or type your question directly.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles all inline button clicks across the main menu and diploma browsing pages.
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    # 1. Display list of diplomas (skips json metadata)
    if data == 'browse_courses':
        keyboard = []
        for code, info in courses_data.items():
            if code.startswith('_'):
                continue
            keyboard.append([InlineKeyboardButton(f"{info['name']} ({code})", callback_data=f"diploma_{code}")])
        
        keyboard.append([InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a Diploma to view detailed information:", reply_markup=reply_markup)

    # 2. Display specific diploma details & save context memory
    elif data.startswith('diploma_'):
        code = data.split('_')[1]
        info = courses_data.get(code)
        
        if info:
            # Save selected diploma code into persistent user memory
            context.user_data['selected_diploma'] = code
            
            source_url = info.get('source_url', 'https://www.nyp.edu.sg/schools/seg.html')
            
            text = (
                f"**{info['name']} ({code})**\n\n"
                f"**JAE COP Range:** {info['cop']} points\n"
                f"**Description:** {info['description']}\n\n"
                f"**Career Paths:** {', '.join(info['careers'])}\n\n"
                f"📌 _Data verified from official NYP portal._"
            )
            
            keyboard = [
                [InlineKeyboardButton("Official NYP Course Webpage 🔗", url=source_url)],
                [InlineKeyboardButton("« Back to Diplomas List", callback_data='browse_courses')],
                [InlineKeyboardButton("« Main Menu", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    # 3. Display JAE Cut-Off Points table
    elif data == 'show_cop':
        cop_lines = []
        for code, info in courses_data.items():
            if code.startswith('_'):
                continue
            cop_lines.append(f"• **{info['name']} ({code})**: {info['cop']} points")
            
        cop_list = "\n".join(cop_lines)
        keyboard = [[InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"**NYP SEG Cut-Off Points (ELR2B2-C):**\n\n{cop_list}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    # 4. Return to main menu and reset active context
    elif data == 'main_menu':
        context.user_data.pop('selected_diploma', None)
        
        keyboard = [
            [InlineKeyboardButton("Browse SEG Diplomas 🎓", callback_data='browse_courses')],
            [InlineKeyboardButton("Check Cut-Off Points (COP) 📊", callback_data='show_cop')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Welcome to the NYP SEG Course Advising Bot! Select an option below or type your question directly.",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles user chat messages and passes context-aware instructions to Gemini AI.
    """
    user_text = update.message.text.strip()
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Main Menu", callback_data='main_menu')]])

    # Fast local response for webpage requests
    if any(word in user_text.lower() for word in ["link", "webpage", "website"]):
        await update.message.reply_text(
            "Here is the official NYP School of Engineering website: https://www.nyp.edu.sg/schools/seg.html",
            reply_markup=reply_markup
        )
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Retrieve currently selected diploma from user_data context
    active_diploma_code = context.user_data.get('selected_diploma')
    active_diploma_info = courses_data.get(active_diploma_code) if active_diploma_code else None

    context_prompt = ""
    if active_diploma_info:
        yr2_modules = ", ".join(active_diploma_info.get("modules_yr2", []))
        context_prompt = f"""
        Active Context: The user currently has the diploma "{active_diploma_info['name']} ({active_diploma_code})" selected.
        Year 2 modules for this specific course: {yr2_modules if yr2_modules else 'Check dataset'}.
        If the user asks follow-up or contextual questions (e.g., 'what modules do year 2 students study?'), respond specifically for {active_diploma_info['name']}.
        If they explicitly ask about a different course or a general topic, answer that query directly instead.
        """

    try:
        response_text = await get_ai_response(user_text, context_prompt)
        await update.message.reply_text(response_text, reply_markup=reply_markup)
        
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