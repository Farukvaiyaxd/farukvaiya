import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime, timedelta
import random
import pytz

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8380869007:AAFop4k07N5Sc1AaD3vFbrudyh3iiHTdvto')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '7835226724'))

# Global variables
current_gemini_api_key = GEMINI_API_KEY
model = None
current_model_name = 'gemini-1.5-flash'
custom_welcome_message = None
current_language = 'Bengali'
last_emoji_index = -1

# Available models
AVAILABLE_MODELS = [
    {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash', 'description': '🎯 Stable & reliable'},
    {'name': 'gemini-1.5-pro', 'display': 'Gemini 1.5 Pro', 'description': '🧠 Most intelligent'},
]

# Butterfly emojis
BUTTERFLY_EMOJIS = ["🦋", "🦋✨", "🦋🌟", "🦋💫"]

# Statistics tracking
user_statistics = {}
api_usage = {}
user_limits = {'daily_messages': 100, 'hourly_messages': 20, 'api_calls': 50}
conversation_context = {}
group_activity = {}

def initialize_gemini_model(api_key, model_name='gemini-1.5-flash'):
    global model, current_gemini_api_key, current_model_name
    try:
        logger.info(f"Attempting to configure Gemini API with model {model_name}")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        current_gemini_api_key = api_key
        current_model_name = model_name
        logger.info(f"Successfully initialized Gemini model: {model_name}")
        return True, f"✅ Gemini API configured successfully with model {model_name}!"
    except Exception as e:
        logger.error(f"Failed to initialize Gemini API with model {model_name}: {str(e)}")
        return False, f"❌ Error configuring Gemini API: {str(e)}"

if GEMINI_API_KEY:
    success, message = initialize_gemini_model(GEMINI_API_KEY)
    if success:
        logger.info("Gemini API initialized from environment variable")
    else:
        logger.error(f"Failed to initialize Gemini API: {message}")
else:
    logger.warning("GEMINI_API_KEY not set. Use /api command to configure.")

class TelegramGeminiBot:
    # ... (এখানে ওপরে দেওয়া কোডের পুরো বডি থাকবে, আগের উত্তরেই পুরোটা ছিল)

    # For brevity, please copy the full class code from the previous main.py answer!

if __name__ == '__main__':
    bot = TelegramGeminiBot()
    asyncio.run(bot.run())