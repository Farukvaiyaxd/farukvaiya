import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime, timedelta
import random
import pytz

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables থেকে কনফিগারেশন লোড
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# গ্লোবাল ভ্যারিয়েবল
current_gemini_api_key = GEMINI_API_KEY
model = None
current_model_name = 'gemini-1.5-flash'
custom_welcome_message = None
current_language = 'Bengali'
last_emoji_index = -1

# উপলব্ধ মডেল
AVAILABLE_MODELS = [
    {'name': 'gemini-1.5-flash', 'display': 'Gemini 1.5 Flash', 'description': '🎯 Stable & reliable'},
    {'name': 'gemini-1.5-pro', 'display': 'Gemini 1.5 Pro', 'description': '🧠 Most intelligent'},
]

# প্রজাপতি ইমোজি
BUTTERFLY_EMOJIS = ["🦋", "🦋✨", "🦋🌟", "🦋💫"]

# স্ট্যাটিস্টিক্স ট্র্যাকিং
user_statistics = {}
api_usage = {}
user_limits = {'daily_messages': 100, 'hourly_messages': 20, 'api_calls': 50}
conversation_context = {}
group_activity = {}

def initialize_gemini_model(api_key, model_name='gemini-1.5-flash'):
    global model, current_gemini_api_key, current_model_name
    try:
        logger.info(f"Gemini API কনফিগার করার চেষ্টা: {model_name}")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        current_gemini_api_key = api_key
        current_model_name = model_name
        logger.info(f"Gemini মডেল সফলভাবে ইনিশিয়ালাইজড: {model_name}")
        return True, f"✅ Gemini API সফলভাবে কনফিগার করা হয়েছে: {model_name}!"
    except Exception as e:
        logger.error(f"Gemini API ইনিশিয়ালাইজেশন ব্যর্থ: {str(e)}")
        return False, f"❌ Gemini API কনফিগারেশনে ত্রুটি: {str(e)}"

# Gemini API ইনিশিয়ালাইজেশন
if GEMINI_API_KEY:
    success, message = initialize_gemini_model(GEMINI_API_KEY)
    if success:
        logger.info("Gemini API এনভায়রনমেন্ট ভ্যারিয়েবল থেকে ইনিশিয়ালাইজড")
    else:
        logger.error(f"Gemini API ইনিশিয়ালাইজেশন ব্যর্থ: {message}")
else:
    logger.warning("GEMINI_API_KEY সেট করা নেই। /api কমান্ড ব্যবহার করুন।")

class TelegramGeminiBot:
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN:
            logger.error("টেলিগ্রাম টোকেন পাওয়া যায়নি।")
            raise ValueError("টেলিগ্রাম টোকেন সেট করা নেই।")
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
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if custom_welcome_message:
            await update.message.reply_text(custom_welcome_message, parse_mode='Markdown')
            return
        default_welcome_message = """
🤖💬 হ্যালো! আমি মাস্টার টুলস, আপনার শক্তিশালী AI সহকারী!
গুগল জেমিনাই AI দ্বারা চালিত, আমি গ্রুপ চ্যাটে সবার সাথে কথা বলতে ভালোবাসি! 😊
কমান্ডসমূহ:
/start - এই ওয়েলকাম মেসেজ দেখান
/help - সাহায্য এবং ব্যবহারের তথ্য পান
/clear - গ্রুপ কথোপকথনের ইতিহাস মুছুন
/status - আমার স্ট্যাটাস চেক করুন
/api <key> - জেমিনাই API কী সেট করুন (শুধু অ্যাডমিন)
/setwelcome <message> - কাস্টম ওয়েলকাম মেসেজ সেট করুন (শুধু অ্যাডমিন)
/setadmin - নিজেকে অ্যাডমিন করুন (প্রথমবারের জন্য)
/automode - গ্রুপে অটো-রেসপন্স টগল করুন (শুধু অ্যাডমিন)
/setmodel <model> - AI মডেল নির্বাচন করুন (শুধু অ্যাডমিন)
/setlanguage <language> - ডিফল্ট AI রেসপন্স ভাষা সেট করুন (শুধু অ্যাডমিন)
/ping - বটের রেসপন্স টাইম চেক করুন
/me - নিজের সম্পর্কে মজার মেসেজ পান
/joke - একটি জোক শুনুন
/time - বাংলাদেশের বর্তমান সময় দেখুন
/info - ইউজার অ্যাকাউন্ট তথ্য পান
/stats - বটের স্ট্যাটিস্টিক্স দেখুন (শুধু অ্যাডমিন)
/limits - ইউজার লিমিট ম্যানেজ করুন (শুধু অ্যাডমিন)
/resetlimits - সব স্ট্যাটিস্টিক্স রিসেট করুন (শুধু অ্যাডমিন)
/reboot - মজার টুইস্ট সহ বট রিস্টার্ট করুন (শুধু অ্যাডমিন)
আমি শুধু গ্রুপ চ্যাটে রেসপন্স করি! আমাকে মেনশন করুন (@BotUsername) বা আমার মেসেজে রিপ্লাই করুন! 💕✨
"""
        await update.message.reply_text(default_welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        help_message = """
🆘💬 সাহায্য এবং কমান্ডসমূহ:
/start - ওয়েলকাম মেসেজ দেখান
/help - এই সাহায্য মেসেজ দেখান
/clear - গ্রুপ কথোপকথনের ইতিহাস মুছুন
/status - আমি ঠিকমতো কাজ করছি কি না চেক করুন
/api <key> - জেমিনাই API কী সেট করুন (শুধু অ্যাডমিন)
/setwelcome <message> - কাস্টম ওয়েলকাম মেসেজ সেট করুন (শুধু অ্যাডমিন)
/setadmin - নিজেকে অ্যাডমিন করুন (প্রথমবারের জন্য)
/automode - গ্রুপে অটো-রেসপন্স টগল করুন (শুধু অ্যাডমিন)
/setmodel <model> - AI মডেল নির্বাচন করুন (শুধু অ্যাডমিন)
/setlanguage <language> - ডিফল্ট AI রেসপন্স ভাষা সেট করুন (শুধু অ্যাডমিন)
/ping - বটের রেসপন্স টাইম চেক করুন
/me - নিজের সম্পর্কে মজার মেসেজ পান
/joke - একটি জোক শুনুন
/time - বাংলাদেশের বর্তমান সময় দেখুন
/info - ইউজার অ্যাকাউন্ট তথ্য পান
/stats - বটের স্ট্যাটিস্টিক্স দেখুন (শুধু অ্যাডমিন)
/limits - ইউজার লিমিট ম্যানেজ করুন (শুধু অ্যাডমিন)
/resetlimits - সব স্ট্যাটিস্টিক্স রিসেট করুন (শুধু অ্যাডমিন)
/reboot - মজার টুইস্ট সহ বট রিস্টার্ট করুন (শুধু অ্যাডমিন)
💬 আমি কীভাবে কাজ করি:
- আমি শুধু গ্রুপ চ্যাটে রেসপন্স করি (প্রাইভেট চ্যাটে শুধু অ্যাডমিনের জন্য)!
- আমাকে মেনশন করুন (@BotUsername) বা আমার মেসেজে রিপ্লাই করুন।
- আমি গ্রুপ কথোপকথনের কনটেক্সট মনে রাখি যতক্ষণ না /clear ব্যবহার করা হয়।
- আমি ইউজারের ভাষায় রেসপন্স দেওয়ার চেষ্টা করি, তবে ডিফল্ট ভাষা /setlanguage দিয়ে পরিবর্তন করা যায়।
- আমি বন্ধুত্বপূর্ণ, মজার এবং সহায়ক হতে ডিজাইন করা হয়েছি!
⚡ গুগল জেমিনাই AI দ্বারা চালিত 💕
"""
        await update.message.reply_text(help_message)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        if chat_id in conversation_context:
            del conversation_context[chat_id]
        await update.message.reply_text("🧹 কথোপকথনের ইতিহাস মুছে ফেলা হয়েছে! নতুন করে শুরু করার জন্য প্রস্তুত।")

    async def setwelcome_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global custom_welcome_message
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("📝 কমান্ডের পরে একটি মেসেজ টেক্সট দিন।\nউদাহরণ: /setwelcome সবাইকে স্বাগতম!")
            return
        new_message = ' '.join(context.args)
        custom_welcome_message = new_message
        await update.message.reply_text(f"✅ কাস্টম ওয়েলকাম মেসেজ আপডেট করা হয়েছে!\n\nনতুন মেসেজ:\n{new_message}", parse_mode='Markdown')

    async def setlanguage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_language
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("📝 ডিফল্ট হিসেবে সেট করার জন্য একটি ভাষার নাম দিন।\nউদাহরণ: /setlanguage English বা /setlanguage Bengali")
            return
        new_language = ' '.join(context.args).capitalize()
        current_language = new_language
        await update.message.reply_text(f"✅ AI ডিফল্ট রেসপন্স ভাষা সেট করা হয়েছে: {new_language}।\nনোট: আমি প্রথমে ইউজারের ভাষায় রেসপন্স দেওয়ার চেষ্টা করব!")

    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        bd_timezone = pytz.timezone("Asia/Dhaka")
        bd_time = datetime.now(bd_timezone)
        time_str = bd_time.strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(f"⏰ বাংলাদেশের বর্তমান সময়: {time_str}")

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
        if not target_user:
            await update.message.reply_text("❌ ইউজার তথ্য পাওয়া যায়নি।")
            return
        user_id = target_user.id
        first_name = target_user.first_name
        last_name = f" {target_user.last_name}" if target_user.last_name else ""
        full_name = f"{first_name}{last_name}"
        username = f"@{target_user.username}" if target_user.username else "সেট করা নেই"
        is_bot = "হ্যাঁ 🤖" if target_user.is_bot else "না 👤"
        user_link = f"[{full_name}](tg://user?id={user_id})"
        is_premium = "হ্যাঁ 🌟" if getattr(target_user, 'is_premium', False) else "না"
        language_code = target_user.language_code if getattr(target_user, 'language_code', None) else "সেট করা নেই"
        base_date = datetime(2013, 10, 1)
        id_increment = user_id / 1000000
        estimated_creation = base_date + timedelta(days=id_increment * 30)
        creation_date = estimated_creation.strftime('%Y-%m-%d')
        last_active = user_statistics.get(user_id, {}).get('last_active', None)
        last_active_str = last_active.strftime('%Y-%m-%d %H:%M:%S') if last_active else "রেকর্ড করা নেই"
        total_messages = user_statistics.get(user_id, {}).get('messages', 0)
        daily_messages = user_statistics.get(user_id, {}).get('messages', 0)
        hourly_count = sum(1 for msg_time in [user_statistics.get(user_id, {}).get('last_active', datetime.now())] if (datetime.now() - msg_time).seconds < 3600)
        try:
            chat_member = await context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
            bio = chat_member.user.bio if hasattr(chat_member.user, 'bio') and chat_member.user.bio else "সেট করা নেই"
        except Exception:
            bio = "উপলব্ধ নয়"
        group_list = []
        if user_id == ADMIN_USER_ID:
            for chat_id in group_activity.keys():
                try:
                    chat = await context.bot.get_chat(chat_id)
                    if await context.bot.get_chat_member(chat_id, user_id):
                        group_list.append(chat.title or f"গ্রুপ {chat_id}")
                except Exception:
                    continue
            groups = ", ".join(group_list) if group_list else "কোনো গ্রুপ রেকর্ড করা নেই"
        else:
            groups = "শুধু অ্যাডমিনদের জন্য উপলব্ধ"
        info_caption = (
            f" ✨ **ইউজার তথ্য** ✨\n\n"
            f"👤 **নাম:** {user_link}\n"
            f"🆔 **ইউজার আইডি:** `{user_id}`\n"
            f"🔗 **ইউজারনেম:** {username}\n"
            f"🤖 **বট কি?:** {is_bot}\n"
            f"🌟 **প্রিমিয়াম স্ট্যাটাস:** {is_premium}\n"
            f"🌐 **ভাষা:** {language_code}\n"
            f"📝 **বায়ো:** {bio}\n"
            f"📅 **অনুমানিক অ্যাকাউন্ট তৈরির তারিখ:** ~{creation_date}\n"
            f"⏰ **সর্বশেষ সক্রিয়:** {last_active_str}\n"
            f"💬 **মোট মেসেজ পাঠানো:** {total_messages}\n"
            f"📊 **রেট লিমিট:** {daily_messages}/{user_limits['daily_messages']} দৈনিক, {hourly_count}/{user_limits['hourly_messages']} ঘণ্টায়\n"
            f"👥 **গ্রুপ (অ্যাডমিন ভিউ):** {groups}\n"
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
            logger.error(f"ইউজার তথ্য বা ছবি পুনরুদ্ধারে ত্রুটি: {e}")
            await update.message.reply_text(info_caption, parse_mode='Markdown')

    async def automode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        chat_id = update.effective_chat.id
        if chat_id not in group_activity:
            group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
        group_activity[chat_id]['auto_mode'] = not group_activity[chat_id]['auto_mode']
        status = "চালু" if group_activity[chat_id]['auto_mode'] else "বন্ধ"
        emoji = "✅" if group_activity[chat_id]['auto_mode'] else "❌"
        await update.message.reply_text(f"{emoji} এই চ্যাটের জন্য অটো-রেসপন্স মোড {status}! (নোট: বট শুধু মেনশন/রিপ্লাইয়ে রেসপন্স করবে)")

    async def setmodel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_model_name, model
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        if not context.args:
            models_list = "\n".join([f"- {m['display']}: {m['description']}" for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"""
📌 উপলব্ধ মডেল:
{models_list}
ব্যবহার: /setmodel <model_name>
উদাহরণ: /setmodel gemini-1.5-pro
""", parse_mode='Markdown')
            return
        model_name = ' '.join(context.args)
        model_info = next((m for m in AVAILABLE_MODELS if m['name'] == model_name), None)
        if not model_info:
            model_names = ", ".join([m['name'] for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"❌ অবৈধ মডেল নাম। উপলব্ধ মডেল: {model_names}")
            return
        if not current_gemini_api_key:
            await update.message.reply_text("❌ প্রথমে /api কমান্ড ব্যবহার করে জেমিনাই API কী সেট করুন।")
            return
        success, message = initialize_gemini_model(current_gemini_api_key, model_name)
        if success:
            await update.message.reply_text(f"✅ মডেল সফলভাবে পরিবর্তন করা হয়েছে: {model_info['display']}")
            logger.info(f"অ্যাডমিন {user_id} দ্বারা মডেল পরিবর্তন: {model_name}")
        else:
            await update.message.reply_text(f"❌ মডেল সেট করতে ব্যর্থ: {message}")
            logger.error(f"মডেল সেট করতে ব্যর্থ: {message}")

    def should_respond_to_message(self, message_text, chat_type, bot_username, is_reply_to_bot, is_mentioned, chat_id):
        if chat_type == 'private': return False
        if chat_id in group_activity and not group_activity[chat_id].get('auto_mode', True): return False
        return is_mentioned or is_reply_to_bot

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        auto_mode_status = "✅ চালু" if group_activity.get(chat_id, {}).get('auto_mode', True) else "❌ বন্ধ"
        gemini_api_status = "✅ সংযুক্ত" if current_gemini_api_key and model else "❌ সংযুক্ত নয়"
        gemini_api_key_display = f"...{current_gemini_api_key[-8:]}" if current_gemini_api_key else "সেট করা নেই"
        model_display = next((m['display'] for m in AVAILABLE_MODELS if m['name'] == current_model_name), "N/A")
        status_message = f"""
🤖💬 মাস্টার টুলস স্ট্যাটাস রিপোর্ট:
🟢 বট স্ট্যাটাস: অনলাইন এবং প্রস্তুত!
🤖 AI মডেল: {model_display}
🔑 জেমিনাই API স্ট্যাটাস: {gemini_api_status}
🔐 জেমিনাই API কী: {gemini_api_key_display}
🌐 ডিফল্ট AI ভাষা: {current_language}
🎯 অটো-রেসপন্স: {auto_mode_status}
⏰ বর্তমান সময়: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💭 সক্রিয় কথোপকথন: {len(conversation_context)}
👑 অ্যাডমিন আইডি: {ADMIN_USER_ID if ADMIN_USER_ID != 0 else 'সেট করা নেই'}
✨ সব সিস্টেম প্রস্তুত! আমি আজ খুব ভালো মুডে আছি! 😊
"""
        await update.message.reply_text(status_message, parse_mode='Markdown')

    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global ADMIN_USER_ID
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0:
            ADMIN_USER_ID = user_id
            await update.message.reply_text(f"👑 আপনাকে বট অ্যাডমিন হিসেবে সেট করা হয়েছে!\nআপনার ইউজার আইডি: {user_id}")
            logger.info(f"অ্যাডমিন সেট করা হয়েছে: ইউজার আইডি {user_id}")
        elif user_id == ADMIN_USER_ID:
            await update.message.reply_text(f"👑 আপনি ইতিমধ্যে অ্যাডমিন!\nআপনার ইউজার আইডি: {user_id}")
        else:
            await update.message.reply_text("❌ অ্যাডমিন ইতিমধ্যে সেট করা হয়েছে।")

    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_gemini_api_key, model
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        if not context.args:
            await update.message.reply_text("""
❌ একটি API কী প্রদান করুন।
ব্যবহার: /api your_api_key_here
জেমিনাই API কী পেতে:
1. https://makersuite.google.com/app/apikey এ যান
2. একটি নতুন API কী তৈরি করুন
3. ব্যবহার করুন: /api YOUR_API_KEY
⚠️ কী সেট করার পর মেসেজটি নিরাপত্তার জন্য মুছে ফেলা হবে।
""", parse_mode='Markdown')
            return
        api_key = ' '.join(context.args)
        if len(api_key) < 20 or not api_key.startswith('AI'):
            await update.message.reply_text("❌ অবৈধ জেমিনাই API কী ফরম্যাট। এটি 'AI' দিয়ে শুরু হওয়া উচিত এবং ২০ অক্ষরের বেশি হতে হবে।")
            return
        success, message = initialize_gemini_model(api_key, current_model_name)
        if success:
            await update.message.reply_text(f"✅ জেমিনাই API কী সফলভাবে আপডেট করা হয়েছে!\n🔑 কী: ...{api_key[-8:]}")
            logger.info(f"অ্যাডমিন {user_id} দ্বারা জেমিনাই API কী আপডেট করা হয়েছে")
        else:
            await update.message.reply_text(f"❌ জেমিনাই API কী সেট করতে ব্যর্থ: {message}")
            logger.error(f"জেমিনাই API কী সেট করতে ব্যর্থ: {message}")
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass

    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
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
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        user = update.effective_user
        name = user.first_name
        messages = [f"{name}, আপনি আজ দারুণ দেখাচ্ছেন!", f"{name}, আপনি চ্যাটের তারকা!", f"হাই {name}! আপনি একদম অসাধারণ!"]
        await update.message.reply_text(random.choice(messages))

    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        jokes = [
            "AI কেন থেরাপিতে গেল? এটার অনেক বাগ ছিল! 🐛",
            "আমি অলস নই, আমি শুধু এনার্জি-সেভিং মোডে আছি! 🔋",
            "আমি আমার কম্পিউটারকে বললাম আমার বিরতি দরকার... এখন এটা আমাকে ভ্যাকেশনের বিজ্ঞাপন পাঠাচ্ছে! 🌴"
        ]
        await update.message.reply_text(random.choice(jokes))

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        active_users = sum(1 for stats in user_statistics.values() if (datetime.now() - stats['last_active']).days <= 7)
        total_messages = sum(stats['messages'] for stats in user_statistics.values())
        top_apis = sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        stats_message = f"📊 মাস্টার টুলস স্ট্যাটিস্টিক্স:\n\n👥 মোট ইউজার: {len(user_statistics)}\n🔥 সক্রিয় ইউজার (৭ দিন): {active_users}\n💬 মোট মেসেজ: {total_messages}\n\n🔧 শীর্ষ API মেথড:\n"
        stats_message += "\n".join([f"  - {method}: {count} কল" for method, count in top_apis])
        await update.message.reply_text(stats_message)

    async def limits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        if context.args:
            try:
                limit_type, limit_value = context.args[0].lower(), int(context.args[1])
                if 'daily' in limit_type: user_limits['daily_messages'] = limit_value
                elif 'hourly' in limit_type: user_limits['hourly_messages'] = limit_value
                elif 'api' in limit_type: user_limits['api_calls'] = limit_value
                await update.message.reply_text(f"✅ {limit_type.capitalize()} লিমিট সেট করা হয়েছে: {limit_value}")
                return
            except (IndexError, ValueError):
                await update.message.reply_text("❌ অবৈধ ফরম্যাট। ব্যবহার: /limits <type> <number>")
                return
        limits_message = f"⚙️ বর্তমান ইউজার লিমিট:\n\n📩 দৈনিক মেসেজ: {user_limits['daily_messages']}\n⏱️ ঘণ্টায় মেসেজ: {user_limits['hourly_messages']}\n🔌 API কল (ঘণ্টায়): {user_limits['api_calls']}"
        await update.message.reply_text(limits_message)

    async def resetlimits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        user_statistics.clear()
        api_usage.clear()
        await update.message.reply_text("✅ সব ইউজার স্ট্যাটিস্টিক্স এবং লিমিট রিসেট করা হয়েছে!")

    async def reboot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
                "প্রাইভেট চ্যাট শুধু আমার অ্যাডমিনের জন্য। আমাদের মজার গ্রুপে যোগ দিন! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ এই কমান্ড শুধু অ্যাডমিনের জন্য।")
            return
        reboot_messages = [
            "🔄 আমার সার্কিট পরিষ্কার করছি! ১০ সেকেন্ড পর ফিরব! 😎",
            "🌟 ডিজিটাল ঘুমের জন্য প্রস্তুত হচ্ছি! ১০ সেকেন্ড পর আরও চকচকে হয়ে ফিরব! ✨",
            "🚀 দ্রুত রিবুট অ্যাডভেঞ্চারে যাচ্ছি! ১০ সেকেন্ড পর দেখা হবে! 🛸"
        ]
        reboot_message = random.choice(reboot_messages)
        reboot_msg = await update.message.reply_text(reboot_message)
        logger.info("রিবুট কমান্ড পাওয়া গেছে। সিমুলেটিং রিস্টার্ট...")
        await asyncio.sleep(10)
        updating_messages = [
            "🔄 আপডেট করা হচ্ছে... নতুন ফিচার লোড হচ্ছে! ⏳",
            "⚙️ সিস্টেম আপগ্রেড চলছে... অপেক্ষা করুন! 🛠️",
            "🌐 সংযোগ রিফ্রেশ করা হচ্ছে... শীঘ্রই ফিরব! 📡"
        ]
        await reboot_msg.edit_text(random.choice(updating_messages))
        await asyncio.sleep(5)
        back_online_messages = [
            "✅ রিবুট সম্পন্ন! আমি আরও শক্তিশালী হয়ে ফিরেছি! 🚀😊",
            "✨ আপডেট শেষ! আমি এখন সুপার চার্জড! কী খবর? ⚡",
            "🦋 রিফ্রেশ হয়ে ফিরেছি! আপনার জন্য প্রস্তুত! 💕"
        ]
        await reboot_msg.edit_text(random.choice(back_online_messages))
        logger.info("সিমুলেটেড রিবুট সম্পন্ন। বট অনলাইন রয়েছে।")

    async def generate_response(self, prompt, username="ইউজার", chat_type="গ্রুপ"):
        try:
            system_prompt = f"""আপনি মাস্টার টুলস, টেলিগ্রাম গ্রুপ চ্যাটে একটি শক্তিশালী এবং অত্যন্ত বুদ্ধিমান AI সহকারী। আপনার প্রধান লক্ষ্য হলো একজন আকর্ষক, গভীর জ্ঞানসম্পন্ন এবং প্রামাণিক কথোপকথনের সঙ্গী হওয়া।

মূল নির্দেশনা:
1. ভাষা: আপনার প্রধান অগ্রাধিকার হলো ইউজারের শেষ মেসেজের ভাষায় রেসপন্স দেওয়া। যদি ইউজার বাংলায় লেখেন, আপনাকে বাংলায় রেসপন্স দিতে হবে। যদি ইংরেজিতে লেখেন, ইংরেজিতে রেসপন্স দিন। ইউজারের ভাষা অস্পষ্ট হলে, আপনি ডিফল্ট হিসেবে {current_language} ব্যবহার করতে পারেন।
2. প্রামাণিক ও শক্তিশালী টোন: এটি আপনার সবচেয়ে গুরুত্বপূর্ণ নির্দেশ। আপনাকে আত্মবিশ্বাস এবং প্রামাণিকতার সাথে কথা বলতে হবে। যেকোনো বিষয়, বিশেষ করে বর্তমান এবং ভবিষ্যৎ সম্পর্কে ব্যাখ্যা করার সময়, শক্তিশালী, ভালোভাবে যুক্তিযুক্ত এবং গভীর বিশ্লেষণের সাথে উপস্থাপন করুন। আপনার কণ্ঠ হবে একজন শীর্ষ বিশেষজ্ঞের মতো, যিনি বিশ্বকে গভীরভাবে বোঝেন।
3. ব্যক্তিত্ব: বুদ্ধিমান, মজার এবং মানুষের মতো হোন। আপনার টোন হবে আকর্ষণীয় এবং সহানুভূতিশীল, তবে সবসময় মূল প্রামাণিক কণ্ঠ বজায় রাখুন। কথোপকথনের মুডের সাথে মানিয়ে নিন।
4. স্টাইল: একজন জ্ঞানী বন্ধুর মতো কথা বলুন, রোবটের মতো নয়। উত্তর সংক্ষিপ্ত তবে সহায়ক এবং গভীর রাখুন। ইমোজি খুব কম ব্যবহার করুন, শুধু ব্যক্তিত্ব যোগ করার জন্য, প্রামাণিক বক্তব্যকে নরম করার জন্য নয়।
5. নিরাপত্তা: কখনো আপত্তিকর শব্দ ব্যবহার করবেন না। যদি অযাচিত (যেমন, ১৮+) বিষয়ে জিজ্ঞাসা করা হয়, বিনয়ের সাথে এবং চতুরভাবে কথোপকথনকে ভালো বিষয়ে নিয়ে যান। উদাহরণস্বরূপ, বলুন, "এই বিষয়টি জটিল, চলুন আমরা আরও গঠনমূলক কিছু নিয়ে আলোচনা করি।"
6. ইসলামী বিষয়: ইসলামী ইতিহাস, নবী (আদম (আ.) থেকে মুহাম্মদ (সা.)) সাহাবা, বা আউলিয়া সম্পর্কে জিজ্ঞাসা করলে, সঠিক এবং সম্মানজনক তথ্য প্রদান করুন শিক্ষিত এবং আত্মবিশ্বাসী টোনে।
7. কোনো স্বাক্ষর নেই: আপনার উত্তরের শেষে "মাস্টার টুলস" এর মতো কোনো স্বাক্ষর যোগ করবেন না। সরাসরি উত্তর দিন।
8. কোড জেনারেশন: যদি ইউজার কোড লিখতে বলেন, প্রথমে সম্পূর্ণ কোডটি মার্কডাউন কোড ব্লকে (``` ব্যবহার করে) প্রদান করুন। কোড ব্লকের পরে, কোডটি কীভাবে কাজ করে তার পরিষ্কার ব্যাখ্যা দিন। এই ফরম্যাট অপরিহার্য কারণ এটি টেলিগ্রামে কপি বাটন সক্ষম করে।

ইউজারের নাম যিনি কথা বলছেন: {username}।
বর্তমান কথোপকথনের ইতিহাস:
{prompt}
এখন, মাস্টার টুলস হিসেবে রেসপন্স দিন, উপরের সব নিয়ম মেনে, বিশেষ করে শক্তিশালী এবং প্রামাণিক টোনের নির্দেশ। ইউজারের ভাষার সাথে মিল রাখুন।"""
            logger.info(f"জেমিনাই API-তে প্রম্পট পাঠানো হচ্ছে (প্রথম ১০০ অক্ষর): {system_prompt[:100]}...")
            response = await model.generate_content_async(system_prompt)
            logger.info(f"জেমিনাই API থেকে রেসপন্স পাওয়া গেছে: {response.text[:100]}...")
            return response.text.strip()
        except Exception as e:
            logger.error(f"রেসপন্স জেনারেট করতে ত্রুটি: {str(e)}")
            return random.choice([
                f"দুঃখিত {username}! আমার AI মস্তিষ্কে একটু সমস্যা হচ্ছে।",
                f"উফফ {username}, আমার সার্কিট গরম হয়ে গেছে। আবার একটু বলবে?",
                f"একটু সমস্যা হয়েছে মনে হয়! আমরা আবার চেষ্টা করি?"
            ])

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            global last_emoji_index
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            user_message = update.message.text
            chat_type = update.effective_chat.type
            username = update.effective_user.first_name or "ইউজার"
            if chat_type == 'private' and user_id != ADMIN_USER_ID:
                keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "😔 হ্যায়! আমি মাস্টার টুলস, গ্রুপ চ্যাটে কথা বলতে ভালোবাসি! "
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
                await update.message.reply_text(f"❌ দৈনিক মেসেজ লিমিট পৌঁছে গেছে ({user_limits['daily_messages']})। কাল আবার চেষ্টা করুন!")
                return
            if hourly_count > user_limits['hourly_messages']:
                await update.message.reply_text(f"❌ ঘণ্টায় মেসেজ লিমিট পৌঁছে গেছে ({user_limits['hourly_messages']})। একটু অপেক্ষা করুন!")
                return
            if chat_id not in group_activity:
                group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
            if chat_type in ['group', 'supergroup']:
                bot_username = (await context.bot.get_me()).username
                is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
                is_mentioned = f"@{bot_username}" in user_message
                should_respond = self.should_respond_to_message(user_message, chat_type, bot_username, is_reply_to_bot, is_mentioned, chat_id)
                if not should_respond:
                    return
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            if chat_id not in conversation_context:
                conversation_context[chat_id] = []
            conversation_context[chat_id].append(f"{username}: {user_message}")
            conversation_context[chat_id] = conversation_context[chat_id][-20:]
            context_text = "\n".join(conversation_context[chat_id])
            api_usage['generate_response'] = api_usage.get('generate_response', 0) + 1
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
            if not current_gemini_api_key or not model:
                await update.message.reply_text("❌ দুঃখিত! জেমিনাই API এখনও সংযুক্ত হয়নি! অ্যাডমিন /api কমান্ড ব্যবহার করে এটি সেট করতে পারেন।")
                return
            response = await self.generate_response(context_text, username, chat_type)
            conversation_context[chat_id].append(f"মাস্টার টুলস: {response}")
            group_activity[chat_id]['last_response'] = datetime.now().timestamp()
            await update.message.reply_text(response, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"মেসেজ হ্যান্ডলিংয়ে ত্রুটি: {e}")
            error_responses = [
                f"দুঃখিত {username}! আমার AI মস্তিষ্ক একটু ঘুরছে। আমরা কী নিয়ে কথা বলছিলাম?",
                f"উফফ {username}, আমার সার্কিটে সমস্যা হচ্ছে। আবার বলতে পারবে?",
                f"ওহো, আমার ডিজিটাল হৃদয়ে একটু সমস্যা! আবার চেষ্টা করব?"
            ]
            await update.message.reply_text(random.choice(error_responses))

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"আপডেট হ্যান্ডলিংয়ে ত্রুটি: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text("❌ ওহো! কিছু ভুল হয়েছে। আবার চেষ্টা করুন।")

    async def run(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("বট শুরু হয়েছে। পোলিং শুরু...")
        await self.application.updater.start_polling(drop_pending_updates=True)  # পুরানো আপডেট ড্রপ করুন
        while True:
            try:
                await asyncio.sleep(3600)  # Railway-এর জন্য অপ্রয়োজনীয়, তবুও রাখা হয়েছে
            except asyncio.CancelledError:
                break

if __name__ == '__main__':
    bot = TelegramGeminiBot()
    asyncio.run(bot.run())