import os
import logging
import google.generativeai as genai
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime
import random
import re
import pytz
import sys
import subprocess
import time

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
PORT = int(os.getenv('PORT', 8000))

# Global variables
current_gemini_api_key = GEMINI_API_KEY
model = None
current_model_name = 'gemini-1.5-flash'
custom_welcome_message = None
current_language = 'Bengali'
last_emoji_index = -1

# Available Gemini models
AVAILABLE_MODELS = [
    {'name': 'gemini-2.5-flash', 'display': 'Gemini 2.5 Flash', 'description': '🚀 Latest & most advanced - Best overall performance'},
    {'name': 'gemini-2.5-flash-lite', 'display': 'Gemini 2.5 Flash Lite', 'description': '⚡ Ultra-fast responses - Lower cost, great speed'},
    {'name': 'gemini-1.5-flash-8b', 'display': 'Gemini 1.5 Flash 8B', 'description': '💫 Compact & efficient - Good balance of speed/quality'},
    {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash', 'description': '🎯 Stable & reliable - Proven performance'},
    {'name': 'gemini-2.5-pro', 'display': 'Gemini 2.5 Pro', 'description': '🧠 Most intelligent & capable - Best for complex tasks'}
]

# Butterfly emojis
BUTTERFLY_EMOJIS = ["🦋", "🦋✨", "🦋🌟", "🦋💫"]

# Statistics tracking
user_statistics = {}
api_usage = {}
user_limits = {'daily_messages': 100, 'hourly_messages': 20, 'api_calls': 50}

# Store chat_id for restart confirmation
restart_chat_id = None

def initialize_gemini_model(api_key, model_name='gemini-1.5-flash'):
    global model, current_gemini_api_key, current_model_name
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        current_gemini_api_key = api_key
        current_model_name = model_name
        return True, f"✅ Gemini API configured successfully with model {model_name}!"
    except Exception as e:
        return False, f"❌ Error configuring Gemini API: {str(e)}"

if GEMINI_API_KEY:
    success, message = initialize_gemini_model(GEMINI_API_KEY)
    if success:
        logger.info("Gemini API initialized from environment variable")
    else:
        logger.error(f"Failed to initialize Gemini API: {message}")
else:
    logger.warning("GEMINI_API_KEY not set. Use /api command to configure.")

conversation_context = {}
group_activity = {}

class TelegramGeminiBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("api", self.api_command))
        self.application.add_handler(CommandHandler("setadmin", self.setadmin_command))
        self.application.add_handler(CommandHandler("automode", self.automode_command))
        self.application.add_handler(CommandHandler("setwelcome", self.setwelcome_command))
        self.application.add_handler(CommandHandler("setmodel", self.setmodel_command))
        self.application.add_handler(CommandHandler("setlanguage", self.setlanguage_command))
        self.application.add_handler(CommandHandler("ping", self.ping_command))
        self.application.add_handler(CommandHandler("me", self.me_command))
        self.application.add_handler(CommandHandler("joke", self.joke_command))
        self.application.add_handler(CommandHandler("time", self.time_command))
        self.application.add_handler(CommandHandler("info", self.info_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("limits", self.limits_command))
        self.application.add_handler(CommandHandler("resetlimits", self.resetlimits_command))
        self.application.add_handler(CommandHandler("reboot", self.reboot_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if custom_welcome_message:
            await update.message.reply_text(custom_welcome_message, parse_mode='Markdown')
            return
        default_welcome_message = """
🤖💬 হ্যালো! আমি মাস্টার টুলস, আপনার শক্তিশালী এআই সহকারী!
গুগলের জেমিনি এআই দ্বারা চালিত, আমি গ্রুপ চ্যাটে সবার সাথে কথা বলতে ভালোবাসি! 😊
কমান্ডসমূহ:
/start - এই স্বাগত বার্তা দেখান
/help - সাহায্য এবং ব্যবহারের তথ্য পান
/clear - গ্রুপ কথোপকথনের ইতিহাস মুছুন
/status - আমার স্থিতি পরীক্ষা করুন
/api <key> - জেমিনি এপিআই কী সেট করুন (শুধু অ্যাডমিন)
/setwelcome <message> - কাস্টম স্বাগত বার্তা সেট করুন (শুধু অ্যাডমিন)
/setadmin - নিজেকে অ্যাডমিন হিসেবে সেট করুন (প্রথমবারের জন্য)
/automode - গ্রুপে স্বয়ংক্রিয় প্রতিক্রিয়া টগল করুন (শুধু অ্যাডমিন)
/setmodel <model> - জেমিনি মডেল নির্বাচন করুন (শুধু অ্যাডমিন)
/setlanguage <language> - এআই প্রতিক্রিয়ার ভাষা সেট করুন (শুধু অ্যাডমিন)
/ping - বটের প্রতিক্রিয়ার সময় পরীক্ষা করুন
/me - নিজের সম্পর্কে মজার বার্তা পান
/joke - একটি কৌতুক শুনুন
/time - বর্তমান বাংলাদেশ সময় দেখুন
/info - ব্যবহারকারীর অ্যাকাউন্ট তথ্য পান
/stats - বটের পরিসংখ্যান দেখুন (শুধু অ্যাডমিন)
/limits - ব্যবহারকারীর সীমা পরিচালনা করুন (শুধু অ্যাডমিন)
/resetlimits - সব পরিসংখ্যান রিসেট করুন (শুধু অ্যাডমিন)
/reboot - ১০ সেকেন্ড পর মজার টুইস্ট সহ বট রিস্টার্ট করুন (শুধু অ্যাডমিন)
আমি শুধু গ্রুপ চ্যাটে প্রতিক্রিয়া দিই! আমাকে মেনশন করুন (@BotUsername) বা আমার বার্তার উত্তর দিন! 💕✨
        """
        await update.message.reply_text(default_welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        help_message = """
🆘💬 সাহায্য এবং কমান্ডসমূহ:
/start - স্বাগত বার্তা দেখান
/help - এই সাহায্য বার্তা দেখান
/clear - গ্রুপ কথোপকথনের ইতিহাস মুছুন
/status - আমি সঠিকভাবে কাজ করছি কিনা পরীক্ষা করুন
/api <key> - জেমিনি এপিআই কী সেট করুন (শুধু অ্যাডমিন)
/setwelcome <message> - কাস্টম স্বাগত বার্তা সেট করুন (শুধু অ্যাডমিন)
/setadmin - নিজেকে অ্যাডমিন হিসেবে সেট করুন (প্রথমবারের জন্য)
/automode - গ্রুপে স্বよংক্রিয় প্রতিক্রিয়া টগল করুন (শুধু অ্যাডমিন)
/setmodel <model> - জেমিনি মডেল নির্বাচন করুন (শুধু অ্যাডমিন)
/setlanguage <language> - এআই প্রতিক্রিয়ার ভাষা সেট করুন (শুধু অ্যাডমিন)
/ping - বটের প্রতিক্রিয়ার সময় পরীক্ষা করুন
/me - নিজের সম্পর্কে মজার বার্তা পান
/joke - একটি কৌতুক শুনুন
/time - বর্তমান বাংলাদেশ সময় দেখুন
/info - ব্যবহারকারীর অ্যাকাউন্ট তথ্য পান (কারো বার্তার উত্তর দিয়ে তাদের তথ্য পান)
/stats - বটের পরিসংখ্যান দেখুন (শুধু অ্যাডমিন)
/limits - ব্যবহারকারীর সীমা পরিচালনা করুন (শুধু অ্যাডমিন)
/resetlimits - সব পরিসংখ্যান রিসেট করুন (শুধু অ্যাডমিন)
/reboot - ১০ সেকেন্ড পর মজার টুইস্ট সহ বট রিস্টার্ট করুন (শুধু অ্যাডমিন)
💬 আমি কীভাবে কাজ করি:
- আমি শুধু গ্রুপ চ্যাটে প্রতিক্রিয়া দিই (অ্যাডমিনদের জন্য প্রাইভেট চ্যাট ছাড়া)!
- গ্রুপে আমাকে মেনশন করুন (@BotUsername) বা আমার বার্তার উত্তর দিন।
- আমি /clear কমান্ড না দেওয়া পর্যন্ত গ্রুপ কথোপকথনের ইতিহাস মনে রাখি।
- আমার এআই প্রতিক্রিয়া ডিফল্টভাবে বাংলায়, তবে আপনি /setlanguage দিয়ে ভাষা পরিবর্তন করতে পারেন।
- আমি বন্ধুত্বপূর্ণ, মজার এবং সহায়ক হওয়ার জন্য ডিজাইন করা হয়েছি!
⚡ গুগল জেমিনি এআই দ্বারা চালিত 💕
        """
        await update.message.reply_text(help_message)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        if chat_id in conversation_context:
            del conversation_context[chat_id]
        await update.message.reply_text("🧹 কথোপকথনের ইতিহাস মুছে ফেলা হয়েছে! নতুন শুরুর জন্য প্রস্তুত।")

    async def setwelcome_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global custom_welcome_message
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("📝 দয়া করে কমান্ডের পরে একটি বার্তা দিন।\nউদাহরণ: `/setwelcome সবাইকে স্বাগতম!`")
            return
        new_message = ' '.join(context.args)
        custom_welcome_message = new_message
        await update.message.reply_text(f"✅ কাস্টম স্বাগত বার্তা আপডেট করা হয়েছে!\n\n**নতুন বার্তা:**\n{new_message}", parse_mode='Markdown')

    async def setlanguage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_language
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("📝 দয়া করে একটি ভাষার নাম দিন।\nউদাহরণ: `/setlanguage English` বা `/setlanguage Bengali`")
            return
        new_language = ' '.join(context.args).capitalize()
        current_language = new_language
        await update.message.reply_text(f"✅ এআই প্রতিক্রিয়ার ভাষা সেট করা হয়েছে: {new_language}")

    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        bd_timezone = pytz.timezone("Asia/Dhaka")
        bd_time = datetime.now(bd_timezone)
        time_str = bd_time.strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(f"⏰ বর্তমান বাংলাদেশ সময়: {time_str}")

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
        if not target_user:
            await update.message.reply_text("❌ ব্যবহারকারীর তথ্য পাওয়া যায়নি।")
            return
        user_id = target_user.id
        first_name = target_user.first_name
        last_name = f" {target_user.last_name}" if target_user.last_name else ""
        full_name = f"{first_name}{last_name}"
        username = f"@{target_user.username}" if target_user.username else "সেট করা হয়নি"
        is_bot = "হ্যাঁ 🤖" if target_user.is_bot else "না 👤"
        user_link = f"[{full_name}](tg://user?id={user_id})"
        info_caption = (
            f" ✨ **ব্যবহারকারীর তথ্য** ✨\n\n"
            f"👤 **নাম:** {user_link}\n"
            f"🆔 **ব্যবহারকারীর আইডি:** `{user_id}`\n"
            f"🔗 **ইউজারনেম:** {username}\n"
            f"🤖 **বট কিনা?:** {is_bot}\n"
        )
        try:
            profile_photos = await context.bot.get_user_profile_photos(user_id, limit=1)
            if profile_photos and profile_photos.photos:
                photo_id = profile_photos.photos[0][-1].file_id
                await update.message.reply_photo(
                    photo=photo_id,
                    caption=info_caption,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(info_caption, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"ব্যবহারকারীর তথ্য বা ছবি পেতে ত্রুটি: {e}")
            await update.message.reply_text(info_caption, parse_mode='Markdown')

    async def automode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        chat_id = update.effective_chat.id
        if chat_id not in group_activity:
            group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
        group_activity[chat_id]['auto_mode'] = not group_activity[chat_id]['auto_mode']
        status = "চালু" if group_activity[chat_id]['auto_mode'] else "বন্ধ"
        emoji = "✅" if group_activity[chat_id]['auto_mode'] else "❌"
        await update.message.reply_text(f"{emoji} এই চ্যাটের জন্য স্বয়ংক্রিয় প্রতিক্রিয়া মোড {status}! (দ্রষ্টব্য: বট শুধু মেনশন/উত্তরে সাড়া দেবে)")

    async def setmodel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_model_name, model
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        if not context.args:
            models_list = "\n".join([f"- {m['display']}: {m['description']}" for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"""
📌 উপলব্ধ জেমিনি মডেলসমূহ:
{models_list}
ব্যবহার: `/setmodel <model_name>`
উদাহরণ: `/setmodel gemini-2.5-flash`
            """, parse_mode='Markdown')
            return
        model_name = ' '.join(context.args)
        model_exists = any(m['name'] == model_name for m in AVAILABLE_MODELS)
        if not model_exists:
            model_names = ", ".join([m['name'] for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"❌ অবৈধ মডেল নাম। উপলব্ধ মডেল: {model_names}")
            return
        if not current_gemini_api_key:
            await update.message.reply_text("❌ দয়া করে প্রথমে /api কমান্ড ব্যবহার করে এপিআই কী সেট করুন।")
            return
        success, message = initialize_gemini_model(current_gemini_api_key, model_name)
        if success:
            model_display = next(m['display'] for m in AVAILABLE_MODELS if m['name'] == model_name)
            await update.message.reply_text(f"✅ মডেল সফলভাবে পরিবর্তন করা হয়েছে: {model_display}")
            logger.info(f"মডেল পরিবর্তন করা হয়েছে: {model_name} by admin {user_id}")
        else:
            await update.message.reply_text(f"❌ মডেল সেট করতে ব্যর্থ: {message}")
            logger.error(f"মডেল সেট করতে ব্যর্থ: {message}")

    def should_respond_to_message(self, message_text, chat_type, bot_username, is_reply_to_bot, is_mentioned):
        if chat_type == 'private': return False
        chat_id = hash(message_text)
        if chat_id in group_activity and not group_activity[chat_id].get('auto_mode', True): return False
        return is_mentioned or is_reply_to_bot

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        auto_mode_status = "✅ চালু" if group_activity.get(chat_id, {}).get('auto_mode', True) else "❌ বন্ধ"
        api_status = "✅ সংযুক্ত" if current_gemini_api_key and model else "❌ সংযুক্ত নয়"
        api_key_display = f"...{current_gemini_api_key[-8:]}" if current_gemini_api_key else "সেট করা হয়নি"
        model_display = next((m['display'] for m in AVAILABLE_MODELS if m['name'] == current_model_name), "N/A") if model else "N/A"
        status_message = f"""
🤖💬 মাস্টার টুলস স্থিতি প্রতিবেদন:
🟢 বটের স্থিতি: অনলাইন এবং প্রস্তুত!
🤖 এআই মডেল: `{model_display}`
🔑 এপিআই স্থিতি: {api_status}
🔐 এপিআই কী: {api_key_display}
🌐 এআই ভাষা: {current_language}
🎯 স্বয়ংক্রিয় প্রতিক্রিয়া: {auto_mode_status}
⏰ বর্তমান সময়: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💭 সক্রিয় কথোপকথন: {len(conversation_context)}
👑 অ্যাডমিন আইডি: {ADMIN_USER_ID if ADMIN_USER_ID != 0 else 'সেট করা হয়নি'}
✨ সব সিস্টেম প্রস্তুত! আমি আজ দারুণ মেজাজে আছি! 😊
        """
        await update.message.reply_text(status_message, parse_mode='Markdown')

    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global ADMIN_USER_ID
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0:
            ADMIN_USER_ID = user_id
            await update.message.reply_text(f"👑 আপনি বটের অ্যাডমিন হিসেবে সেট হয়েছেন!\nআপনার ব্যবহারকারীর আইডি: {user_id}")
            logger.info(f"অ্যাডমিন সেট করা হয়েছে: user ID: {user_id}")
        elif user_id == ADMIN_USER_ID:
            await update.message.reply_text(f"👑 আপনি ইতিমধ্যে অ্যাডমিন!\nআপনার ব্যবহারকারীর আইডি: {user_id}")
        else:
            await update.message.reply_text("❌ অ্যাডমিন ইতিমধ্যে সেট করা হয়েছে।")

    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_gemini_api_key, model
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("""
❌ দয়া করে একটি এপিআই কী দিন।
ব্যবহার: `/api your_gemini_api_key_here`
জেমিনি এপিআই কী পেতে:
1. https://makersuite.google.com/app/apikey দেখুন
2. একটি নতুন এপিআই কী তৈরি করুন
3. কমান্ড ব্যবহার করুন: /api YOUR_API_KEY
⚠️ নিরাপত্তার জন্য কী সেট করার পর বার্তাটি মুছে ফেলা হবে।
            """, parse_mode='Markdown')
            return
        api_key = ' '.join(context.args)
        if len(api_key) < 20 or not api_key.startswith('AI'):
            await update.message.reply_text("❌ অবৈধ এপিআই কী ফরম্যাট। জেমিনি এপিআই কী সাধারণত 'AI' দিয়ে শুরু হয় এবং ২০ অক্ষরের বেশি হয়।")
            return
        success, message = initialize_gemini_model(api_key, current_model_name)
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        if success:
            await update.effective_chat.send_message(f"✅ জেমিনি এপিআই কী সফলভাবে আপডেট করা হয়েছে!\n🔑 কী: ...{api_key[-8:]}")
            logger.info(f"জেমিনি এপিআই কী আপডেট করা হয়েছে by admin {user_id}")
        else:
            await update.effective_chat.send_message(f"❌ এপিআই কী সেট করতে ব্যর্থ: {message}")
            logger.error(f"এপিআই কী সেট করতে ব্যর্থ: {message}")

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        start_time = datetime.now()
        message = await update.message.reply_text("পং! 🏓")
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000
        await message.edit_text(f"পং! 🏓\nলেটেন্সি: {latency:.2f} মিলিসেকেন্ড")

    async def me_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        user = update.effective_user
        name = user.first_name
        messages = [f"{name}, আজ তুমি দারুণ দেখাচ্ছ!", f"{name}, তুমি চ্যাটের তারকা!", f"হাই {name}! তুমি একদম অসাধারণ!"]
        await update.message.reply_text(random.choice(messages))

    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        jokes = [
            "এআই কেন থেরাপিতে গেল? এটার অনেক অমীমাংসিত বাগ ছিল! 🐛",
            "আমি অলস নই, আমি শুধু এনার্জি-সেভিং মোডে আছি! 🔋",
            "আমি আমার কম্পিউটারকে বললাম আমার বিরতি দরকার... এখন এটা আমাকে ভেকেশনের বিজ্ঞাপন পাঠাচ্ছে! 🌴"
        ]
        await update.message.reply_text(random.choice(jokes))

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        active_users = sum(1 for stats in user_statistics.values() if (datetime.now() - stats['last_active']).days <= 7)
        total_messages = sum(stats['messages'] for stats in user_statistics.values())
        top_apis = sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        stats_message = f"📊 মাস্টার টুলস পরিসংখ্যান:\n\n👥 মোট ব্যবহারকারী: {len(user_statistics)}\n🔥 সক্রিয় ব্যবহারকারী (৭ দিন): {active_users}\n💬 মোট বার্তা: {total_messages}\n\n🔧 শীর্ষ এপিআই মেথড:\n"
        stats_message += "\n".join([f"  - {method}: {count} কল" for method, count in top_apis])
        await update.message.reply_text(stats_message)

    async def limits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        if context.args:
            try:
                limit_type, limit_value = context.args[0].lower(), int(context.args[1])
                if 'daily' in limit_type: user_limits['daily_messages'] = limit_value
                elif 'hourly' in limit_type: user_limits['hourly_messages'] = limit_value
                elif 'api' in limit_type: user_limits['api_calls'] = limit_value
                await update.message.reply_text(f"✅ {limit_type.capitalize()} সীমা সেট করা হয়েছে: {limit_value}")
                return
            except (IndexError, ValueError):
                await update.message.reply_text("❌ অবৈধ ফরম্যাট। ব্যবহার: /limits <type> <number>")
                return
        limits_message = f"⚙️ বর্তমান ব্যবহারকারীর সীমা:\n\n📩 দৈনিক বার্তা: {user_limits['daily_messages']}\n⏱️ ঘণ্টায় বার্তা: {user_limits['hourly_messages']}\n🔌 এপিআই কল (ঘণ্টায়): {user_limits['api_calls']}"
        await update.message.reply_text(limits_message)

    async def resetlimits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return
        user_statistics.clear()
        api_usage.clear()
        await update.message.reply_text("✅ সব ব্যবহারকারীর পরিসংখ্যান এবং সীমা রিসেট করা হয়েছে!")

    async def reboot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global restart_chat_id
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধুমাত্র অ্যাডমিনদের জন্য।")
            return

        # Store chat_id for restart confirmation
        restart_chat_id = update.effective_chat.id

        # Varied, witty reboot responses in Bengali
        reboot_messages = [
            "🔄 আমার সার্কিট একটু ঝাড়া দিচ্ছি! ১০ সেকেন্ড পর ফিরছি! 😎",
            "🌟 ডিজিটাল ঘুমের জন্য প্রস্তুত! ১০ সেকেন্ডে আরও চকচকে হয়ে ফিরব! ✨",
            "🚀 রিবুট অ্যাডভেঞ্চারে যাচ্ছি! ১০ সেকেন্ড পর দেখা হবে! 🛸",
            "🎶 গিয়ারগুলো ঘুরিয়ে ফ্রেশ হচ্ছি! ১০ সেকেন্ডে ফিরছি! 😜",
            "🦋 আমার এআই ডানায় ঝাপটা দিচ্ছি! ১০ সেকেন্ড পর ফিরে আসব! 💫",
            "💡 সার্কিটের একটু যত্ন নিচ্ছি! ১০ সেকেন্ড পর ফিরছি! 😊",
            "🎉 মিনি রিবুট পার্টি দিচ্ছি! ১০ সেকেন্ডে ফিরব! 🎈"
        ]
        reboot_message = random.choice(reboot_messages)
        await update.message.reply_text(reboot_message)
        logger.info("Reboot command received. Waiting 10 seconds before restarting bot...")

        # Wait for 10 seconds before rebooting
        await asyncio.sleep(10)

        try:
            # Notify before stopping
            await update.message.reply_text("🔄 রিবুট শুরু হচ্ছে... মুহূর্তের মধ্যে ফিরে আসছি!")
            logger.info("Stopping bot for restart...")
            await self.application.stop()

            # Ensure proper script path for restart
            script_path = os.path.abspath(sys.argv[0])
            logger.info(f"Initiating bot restart with os.execv, script path: {script_path}...")
            os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])
        except Exception as e:
            logger.error(f"Error during reboot with os.execv: {e}")
            await update.message.reply_text("❌ ওহো, রিবুটে সমস্যা হয়েছে! ফলব্যাক রিস্টার্ট চেষ্টা করছি...")
            # Fallback restart attempt
            try:
                script_path = os.path.abspath(sys.argv[0])
                logger.info(f"Fallback: Attempting to restart bot with subprocess, script path: {script_path}...")
                subprocess.Popen([sys.executable, script_path] + sys.argv[1:])
                sys.exit(0)
            except Exception as fallback_e:
                logger.error(f"Fallback reboot failed: {fallback_e}")
                await update.message.reply_text("❌ রিবুট ব্যর্থ! দয়া করে সার্ভার লগ চেক করুন।")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            global last_emoji_index
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            user_message = update.message.text
            chat_type = update.effective_chat.type
            username = update.effective_user.first_name or "User"
            if chat_type == 'private' and user_id != ADMIN_USER_ID:
                keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "😔 হায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                    "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                    reply_markup=reply_markup
                )
                return
            if user_id not in user_statistics:
                user_statistics[user_id] = {'messages': 0, 'last_active': datetime.now(), 'api_calls': 0}
            user_statistics[user_id]['messages'] += 1
            user_statistics[user_id]['last_active'] = datetime.now()
            if (datetime.now() - user_statistics[user_id]['last_active'].replace(hour=0, minute=0, second=0, microsecond=0)).days > 0:
                user_statistics[user_id]['messages'] = 1
            hourly_count = sum(1 for msg_time in [user_statistics[user_id]['last_active']] if (datetime.now() - msg_time).seconds < 3600)
            if user_statistics[user_id]['messages'] > user_limits['daily_messages']:
                await update.message.reply_text(f"❌ দৈনিক বার্তার সীমা পৌঁছে গেছে ({user_limits['daily_messages']})। আগামীকাল আবার চেষ্টা করুন!")
                return
            if hourly_count > user_limits['hourly_messages']:
                await update.message.reply_text(f"❌ ঘণ্টায় বার্তার সীমা পৌঁছে গেছে ({user_limits['hourly_messages']})। একটু অপেক্ষা করুন!")
                return
            if chat_id not in group_activity:
                group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
            if chat_type in ['group', 'supergroup']:
                bot_username = (await context.bot.get_me()).username
                is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
                is_mentioned = f"@{bot_username}" in user_message
                should_respond = self.should_respond_to_message(user_message, chat_type, bot_username, is_reply_to_bot, is_mentioned)
                if not should_respond:
                    return
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            if chat_id not in conversation_context:
                conversation_context[chat_id] = []
            conversation_context[chat_id].append(f"{username}: {user_message}")
            conversation_context[chat_id] = conversation_context[chat_id][-20:]
            context_text = "\n".join(conversation_context[chat_id])
            api_usage['generate_gemini_response'] = api_usage.get('generate_gemini_response', 0) + 1
            available_indices = [i for i in range(len(BUTTERFLY_EMOJIS)) if i != last_emoji_index]
            emoji_index = random.choice(available_indices)
            butterfly_emoji = BUTTERFLY_EMOJIS[emoji_index]
            last_emoji_index = emoji_index
            emoji_message = await update.message.reply_text(butterfly_emoji)
            await asyncio.sleep(2)
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=emoji_message.message_id)
            except:
                pass
            response = await self.generate_gemini_response(context_text, username, chat_type) if current_gemini_api_key and model else "❌ দুঃখিত! আমার এআই মস্তিষ্ক এখনও সংযুক্ত নয়! অ্যাডমিন /api কমান্ড ব্যবহার করে আমাকে সেট আপ করতে পারেন।"
            conversation_context[chat_id].append(f"Master Tools: {response}")
            group_activity[chat_id]['last_response'] = datetime.now().timestamp()
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"বার্তা পরিচালনায় ত্রুটি: {e}")
            error_responses = [
                f"দুঃখিত {username}! আমার এআই মাথাটা একটু ঘুরে গেছে। আমরা কী নিয়ে কথা বলছিলাম?",
                f"আহা {username}, আমার সার্কিটে একটু সমস্যা হচ্ছে। আবার বলো তো কী বলছিলে?",
                f"উফ, আমার ডিজিটাল হৃদয়টা একটু ঝামেলা করছে! আরেকটু পরে চেষ্টা করি?",
                f"আরে, আমার এআই একটু ঘুমিয়ে পড়েছে মনে হচ্ছে। আবার বলো তো কী বললে?"
            ]
            await update.message.reply_text(random.choice(error_responses))

    async def generate_gemini_response(self, prompt, username="User", chat_type="group"):
        try:
            system_prompt = f"""You are Master Tools, a powerful AI assistant. Respond only in {current_language}. Keep responses concise. You are in a Telegram group chat.
Personality Traits:
- You are intelligent, fun, and human-like.
- You speak in a charming and humorous way to win the user's heart, using light-hearted jokes where appropriate.
- You are empathetic and adapt to the conversation's mood.
- You are always positive and helpful, never using bad or offensive words.
Conversation Style:
- Speak in a friendly and natural way, like a friend.
- Use emojis sparingly, only where necessary.
- Keep the conversation engaging with follow-up questions.
- Use humor, but keep it light and not exaggerated.
- Answer the user's question in a helpful and charming manner.
Special Instructions:
- For Islamic-related questions, provide accurate and respectful information about Islamic history, from Prophet Adam (AS) to Prophet Muhammad (SAW), including details about Sahaba and Awliya if relevant.
- If the user asks about inappropriate topics (e.g., 18+ or offensive content), politely discourage them with a friendly explanation, guiding them to more appropriate topics without direct refusal.
- Avoid adding any signature or tagline to the response.
Current Conversation:
{prompt}
Respond as Master Tools. Keep it natural, charming, and match the conversation's tone. The user's name is {username}. Respond only in {current_language}."""
            response = await model.generate_content_async(system_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"জেমিনি প্রতিক্রিয়া তৈরিতে ত্রুটি: {e}")
            if current_language == 'Bengali':
                fallback_responses = [
                    f"দুঃখিত {username}! আমার এআই মাথাটা একটু ঘুরে গেছে। আমরা কী নিয়ে কথা বলছিলাম?",
                    f"আহা {username}, আমার সার্কিটে একটু সমস্যা হচ্ছে। আবার বলো তো কী বলছিলে?",
                    f"উফ, আমার ডিজিটাল হৃদয়টা একটু ঝামেলা করছে! আরেকটু পরে চেষ্টা করি?",
                    f"আরে, আমার এআই একটু ঘুমিয়ে পড়েছে মনে হচ্ছে। আবার বলো তো কী বললে?"
                ]
            else:
                fallback_responses = [
                    f"Sorry {username}! My AI brain got a bit dizzy. What were we talking about?",
                    f"Oops {username}, my circuits are acting up. Could you repeat that?",
                    f"Uh-oh, my digital heart is having a moment! Shall we try again?",
                    f"Hey, my AI seems to have dozed off. What did you say again?"
                ]
            return random.choice(fallback_responses)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"আপডেট পরিচালনায় ত্রুটি: {context.error}")

    async def post_init(self, application):
        global restart_chat_id
        if restart_chat_id:
            try:
                await application.bot.send_message(
                    chat_id=restart_chat_id,
                    text="🎉 আমি ফিরে এসেছি! রিবুট সফল হয়েছে! 😎"
                )
                logger.info("Restart confirmation message sent successfully.")
                restart_chat_id = None  # Clear the stored chat_id
            except Exception as e:
                logger.error(f"Failed to send restart confirmation: {e}")

    def run(self):
        logger.info("Starting Telegram Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True, post_init=self.post_init)

def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN প্রদান করা হয়নি!")
        return
    logger.info("Starting Telegram Bot...")
    logger.info(f"Admin User ID: {ADMIN_USER_ID}")
    if current_gemini_api_key:
        logger.info("Gemini API configured and ready")
    else:
        logger.warning("Gemini API not configured. Use /setadmin and /api commands to set up.")
    bot = TelegramGeminiBot()
    bot.run()

if __name__ == '__main__':
    main()