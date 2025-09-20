import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, Filters, ContextTypes
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
        self.application.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, self.handle_message))  
        self.application.add_error_handler(self.error_handler)  

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):  
        user_id = update.effective_user.id  
        chat_type = update.effective_chat.type  
        if chat_type == 'private' and user_id != ADMIN_USER_ID:  
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]  
            reply_markup = InlineKeyboardMarkup(keyboard)  
            await update.message.reply_text(  
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "  
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",  
                reply_markup=reply_markup  
            )  
            return  
        if custom_welcome_message:  
            await update.message.reply_text(custom_welcome_message, parse_mode='Markdown')  
            return  
        default_welcome_message = """
🤖💬 Hello! I'm Master Tools, your powerful AI assistant!
Powered by Google Gemini AI, I love chatting with everyone in group chats! 😊
Commands:
/start - Show this welcome message
/help - Get help and usage info
/clear - Clear group conversation history
/status - Check my status
/api <key> - Set Gemini API key (admin only)
/setwelcome <message> - Set custom welcome message (admin only)
/setadmin - Set yourself as admin (first-time only)
/automode - Toggle auto-response in group (admin only)
/setmodel <model> - Select AI model (admin only)
/setlanguage <language> - Set default AI response language (admin only)
/ping - Check bot's response time
/me - Get a fun message about yourself
/joke - Hear a joke
/time - See current Bangladesh time
/info - Get user account info
/stats - View bot statistics (admin only)
/limits - Manage user limits (admin only)
/resetlimits - Reset all statistics (admin only)
/reboot - Restart bot with a fun twist (admin only)
I only respond in group chats! Mention me (@BotUsername) or reply to my messages! 💕✨
"""
        await update.message.reply_text(default_welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):  
        user_id = update.effective_user.id  
        chat_type = update.effective_chat.type  
        if chat_type == 'private' and user_id != ADMIN_USER_ID:  
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]  
            reply_markup = InlineKeyboardMarkup(keyboard)  
            await update.message.reply_text(  
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "  
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",  
                reply_markup=reply_markup  
            )  
            return  
        help_message = """
🆘💬 Help and Commands:
/start - Show welcome message
/help - Show this help message
/clear - Clear group conversation history
/status - Check if I'm working properly
/api <key> - Set Gemini API key (admin only)
/setwelcome <message> - Set custom welcome message (admin only)
/setadmin - Set yourself as admin (first-time only)
/automode - Toggle auto-response in group (admin only)
/setmodel <model> - Select AI model (admin only)
/setlanguage <language> - Set default AI response language (admin only)
/ping - Check bot's response time
/me - Get a fun message about yourself
/joke - Hear a joke
/time - See current Bangladesh time
/info - Get user account info
/stats - View bot statistics (admin only)
/limits - Manage user limits (admin only)
/resetlimits - Reset all statistics (admin only)
/reboot - Restart bot with a fun twist (admin only)
💬 How I work:
- I only respond in group chats (no private chats except for admin)!
- Mention me (@BotUsername) or reply to my messages in groups.
- I remember group conversation context until /clear is used.
- I try to respond in your language, but my default is changeable with /setlanguage.
- I'm designed to be friendly, fun, and helpful!
⚡ Powered by Google Gemini AI 💕
"""
        await update.message.reply_text(help_message)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        if chat_id in conversation_context:
            del conversation_context[chat_id]
        await update.message.reply_text("🧹 Conversation history cleared! Ready to start fresh.")

    async def setwelcome_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global custom_welcome_message
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        if not context.args:
            await update.message.reply_text("📝 Please provide a message text after the command.\nExample: /setwelcome Welcome everyone!")
            return
        new_message = ' '.join(context.args)
        custom_welcome_message = new_message
        await update.message.reply_text(f"✅ Custom welcome message updated!\n\nNew message:\n{new_message}", parse_mode='Markdown')

    async def setlanguage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_language
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        if not context.args:
            await update.message.reply_text("📝 Please provide a language name to set as default.\nExample: /setlanguage English or /setlanguage Bengali")
            return
        new_language = ' '.join(context.args).capitalize()
        current_language = new_language
        await update.message.reply_text(f"✅ AI default response language set to: {new_language}.\nNote: I will still try to reply in the user's language first!")

    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        bd_timezone = pytz.timezone("Asia/Dhaka")
        bd_time = datetime.now(bd_timezone)
        time_str = bd_time.strftime('%Y-%m-%d %H:%M:%S')
        await update.message.reply_text(f"⏰ Current Bangladesh time: {time_str}")

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        target_user = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user  
        if not target_user:  
            await update.message.reply_text("❌ User information not found.")  
            return  
        user_id = target_user.id  
        first_name = target_user.first_name  
        last_name = f" {target_user.last_name}" if target_user.last_name else ""  
        full_name = f"{first_name}{last_name}"  
        username = f"@{target_user.username}" if target_user.username else "Not set"  
        is_bot = "Yes 🤖" if target_user.is_bot else "No 👤"  
        user_link = f"[{full_name}](tg://user?id={user_id})"  
        is_premium = "Yes 🌟" if getattr(target_user, 'is_premium', False) else "No"  
        language_code = target_user.language_code if getattr(target_user, 'language_code', None) else "Not set"  
        base_date = datetime(2013, 10, 1)  
        id_increment = user_id / 1000000  
        estimated_creation = base_date + timedelta(days=id_increment * 30)  
        creation_date = estimated_creation.strftime('%Y-%m-%d')  
        last_active = user_statistics.get(user_id, {}).get('last_active', None)  
        last_active_str = last_active.strftime('%Y-%m-%d %H:%M:%S') if last_active else "Not recorded"  
        total_messages = user_statistics.get(user_id, {}).get('messages', 0)  
        daily_messages = user_statistics.get(user_id, {}).get('messages', 0)  
        hourly_count = sum(1 for msg_time in [user_statistics.get(user_id, {}).get('last_active', datetime.now())] if (datetime.now() - msg_time).seconds < 3600)  
        try:  
            chat_member = await context.bot.get_chat_member(chat_id=update.effective_chat.id, user_id=user_id)  
            bio = chat_member.user.bio if hasattr(chat_member.user, 'bio') and chat_member.user.bio else "Not set"  
        except Exception:  
            bio = "Not available"  
        group_list = []  
        if user_id == ADMIN_USER_ID:  
            for chat_id in group_activity.keys():  
                try:  
                    chat = await context.bot.get_chat(chat_id)  
                    if await context.bot.get_chat_member(chat_id, user_id):  
                        group_list.append(chat.title or f"Group {chat_id}")  
                except Exception:  
                    continue  
            groups = ", ".join(group_list) if group_list else "None recorded"  
        else:  
            groups = "Available to admins only"  
        info_caption = (  
            f" ✨ **User Information** ✨\n\n"  
            f"👤 **Name:** {user_link}\n"  
            f"🆔 **User ID:** `{user_id}`\n"  
            f"🔗 **Username:** {username}\n"  
            f"🤖 **Is Bot?:** {is_bot}\n"  
            f"🌟 **Premium Status:** {is_premium}\n"  
            f"🌐 **Language:** {language_code}\n"  
            f"📝 **Bio:** {bio}\n"  
            f"📅 **Estimated Account Creation:** ~{creation_date}\n"  
            f"⏰ **Last Active:** {last_active_str}\n"  
            f"💬 **Total Messages Sent:** {total_messages}\n"  
            f"📊 **Rate Limits:** {daily_messages}/{user_limits['daily_messages']} daily, {hourly_count}/{user_limits['hourly_messages']} hourly\n"  
            f"👥 **Groups (Admin View):** {groups}\n"  
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
            logger.error(f"Error retrieving user info or photo: {e}")  
            await update.message.reply_text(info_caption, parse_mode='Markdown')

    async def automode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        chat_id = update.effective_chat.id
        if chat_id not in group_activity:
            group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
        group_activity[chat_id]['auto_mode'] = not group_activity[chat_id]['auto_mode']
        status = "Enabled" if group_activity[chat_id]['auto_mode'] else "Disabled"
        emoji = "✅" if group_activity[chat_id]['auto_mode'] else "❌"
        await update.message.reply_text(f"{emoji} Auto-response mode {status} for this chat! (Note: Bot will only respond to mentions/replies)")

    async def setmodel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_model_name, model
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        if not context.args:
            models_list = "\n".join([f"- {m['display']}: {m['description']}" for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"""
📌 Available models:
{models_list}
Usage: /setmodel <model_name>
Example: /setmodel gemini-1.5-pro
""", parse_mode='Markdown')
            return
        model_name = ' '.join(context.args)
        model_info = next((m for m in AVAILABLE_MODELS if m['name'] == model_name), None)
        if not model_info:
            model_names = ", ".join([m['name'] for m in AVAILABLE_MODELS])
            await update.message.reply_text(f"❌ Invalid model name. Available models: {model_names}")
            return
        if not current_gemini_api_key:
            await update.message.reply_text("❌ Please set the Gemini API key first using the /api command.")
            return
        success, message = initialize_gemini_model(current_gemini_api_key, model_name)
        if success:
            await update.message.reply_text(f"✅ Model successfully changed to: {model_info['display']}")
            logger.info(f"Model changed by admin {user_id}: {model_name}")
        else:
            await update.message.reply_text(f"❌ Failed to set model: {message}")
            logger.error(f"Failed to set model: {message}")

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
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        chat_id = update.effective_chat.id
        auto_mode_status = "✅ Enabled" if group_activity.get(chat_id, {}).get('auto_mode', True) else "❌ Disabled"
        gemini_api_status = "✅ Connected" if current_gemini_api_key and model else "❌ Not connected"
        gemini_api_key_display = f"...{current_gemini_api_key[-8:]}" if current_gemini_api_key else "Not set"
        model_display = next((m['display'] for m in AVAILABLE_MODELS if m['name'] == current_model_name), "N/A")
        status_message = f"""
🤖💬 Master Tools Status Report:
🟢 Bot Status: Online and ready!
🤖 AI Model: {model_display}
🔑 Gemini API Status: {gemini_api_status}
🔐 Gemini API Key: {gemini_api_key_display}
🌐 Default AI Language: {current_language}
🎯 Auto-response: {auto_mode_status}
⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💭 Active Conversations: {len(conversation_context)}
👑 Admin ID: {ADMIN_USER_ID if ADMIN_USER_ID != 0 else 'Not set'}
✨ All systems ready! I'm in a great mood today! 😊
"""
        await update.message.reply_text(status_message, parse_mode='Markdown')

    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global ADMIN_USER_ID
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0:
            ADMIN_USER_ID = user_id
            await update.message.reply_text(f"👑 You have been set as the bot admin!\nYour User ID: {user_id}")
            logger.info(f"Admin set: User ID {user_id}")
        elif user_id == ADMIN_USER_ID:
            await update.message.reply_text(f"👑 You are already the admin!\nYour User ID: {user_id}")
        else:
            await update.message.reply_text("❌ Admin has already been set.")

    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_gemini_api_key, model
        user_id = update.effective_user.id
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        if not context.args:
            await update.message.reply_text("""
❌ Please provide an API key.
Usage: /api your_api_key_here
To get a Gemini API key:
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Use: /api YOUR_API_KEY
⚠️ The message will be deleted after setting the key for security.
""", parse_mode='Markdown')
            return
        api_key = ' '.join(context.args)
        if len(api_key) < 20 or not api_key.startswith('AI'):
            await update.message.reply_text("❌ Invalid Gemini API key format. It should start with 'AI' and be over 20 characters.")
            return
        success, message = initialize_gemini_model(api_key, current_model_name)
        if success:
            await update.message.reply_text(f"✅ Gemini API key successfully updated!\n🔑 Key: ...{api_key[-8:]}")
            logger.info(f"Gemini API key updated by admin {user_id}")
        else:
            await update.message.reply_text(f"❌ Failed to set Gemini API key: {message}")
            logger.error(f"Failed to set Gemini API key: {message}")
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
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        start_time = datetime.now()
        message = await update.message.reply_text("Pong! 🏓")
        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds() * 1000
        await message.edit_text(f"Pong! 🏓\nLatency: {latency:.2f} milliseconds")

    async def me_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        user = update.effective_user
        name = user.first_name
        messages = [f"{name}, you look awesome today!", f"{name}, you're the star of the chat!", f"Hi {name}! You're absolutely fantastic!"]
        await update.message.reply_text(random.choice(messages))

    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        jokes = [
            "Why did the AI go to therapy? It had too many unresolved bugs! 🐛",
            "I'm not lazy, I'm just in energy-saving mode! 🔋",
            "I told my computer I needed a break... now it's sending me vacation ads! 🌴"
        ]
        await update.message.reply_text(random.choice(jokes))

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        active_users = sum(1 for stats in user_statistics.values() if (datetime.now() - stats['last_active']).days <= 7)
        total_messages = sum(stats['messages'] for stats in user_statistics.values())
        top_apis = sorted(api_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        stats_message = f"📊 Master Tools Statistics:\n\n👥 Total Users: {len(user_statistics)}\n🔥 Active Users (7 days): {active_users}\n💬 Total Messages: {total_messages}\n\n🔧 Top API Methods:\n"
        stats_message += "\n".join([f"  - {method}: {count} calls" for method, count in top_apis])
        await update.message.reply_text(stats_message)

    async def limits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        if context.args:
            try:
                limit_type, limit_value = context.args[0].lower(), int(context.args[1])
                if 'daily' in limit_type: user_limits['daily_messages'] = limit_value
                elif 'hourly' in limit_type: user_limits['hourly_messages'] = limit_value
                elif 'api' in limit_type: user_limits['api_calls'] = limit_value
                await update.message.reply_text(f"✅ {limit_type.capitalize()} limit set to: {limit_value}")
                return
            except (IndexError, ValueError):
                await update.message.reply_text("❌ Invalid format. Usage: /limits <type> <number>")
                return
        limits_message = f"⚙️ Current User Limits:\n\n📩 Daily Messages: {user_limits['daily_messages']}\n⏱️ Hourly Messages: {user_limits['hourly_messages']}\n🔌 API Calls (Hourly): {user_limits['api_calls']}"
        await update.message.reply_text(limits_message)

    async def resetlimits_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        user_statistics.clear()
        api_usage.clear()
        await update.message.reply_text("✅ All user statistics and limits have been reset!")

    async def reboot_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            keyboard = [[InlineKeyboardButton("Join Our Group", url="https://t.me/VPSHUB_BD_CHAT")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "😔 Hey! I'm Master Tools, and I love chatting in group chats! "
                "Private chats are only for my admin. Join our fun group to talk with me! 🌟",
                reply_markup=reply_markup
            )
            return
        if ADMIN_USER_ID == 0 or user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is for admins only.")
            return
        reboot_messages = [
            "🔄 Dusting off my circuits! I'll be back in 10 seconds! 😎",
            "🌟 Getting ready for a digital nap! I'll be back shinier in 10 seconds! ✨",
            "🚀 Going on a quick reboot adventure! See you in 10 seconds! 🛸"
        ]
        reboot_message = random.choice(reboot_messages)
        reboot_msg = await update.message.reply_text(reboot_message)
        logger.info("Reboot command received. Simulating restart...")
        await asyncio.sleep(10)
        updating_messages = [
            "🔄 Updating... Loading new features! ⏳",
            "⚙️ System upgrade in progress... Please wait! 🛠️",
            "🌐 Refreshing connection... I'll be back soon! 📡"
        ]
        await reboot_msg.edit_text(random.choice(updating_messages))
        await asyncio.sleep(5)
        back_online_messages = [
            "✅ Reboot complete! I'm back, stronger than ever! 🚀😊",
            "✨ Update finished! I'm super charged now! What's up? ⚡",
            "🦋 Refreshed and back! Ready for you! 💕"
        ]
        await reboot_msg.edit_text(random.choice(back_online_messages))
        logger.info("Simulated reboot complete. Bot remains online.")

    async def generate_response(self, prompt, username="User", chat_type="group"):
        try:
            system_prompt = f"""You are Master Tools, a powerful and highly intelligent AI assistant in a Telegram group chat. Your main goal is to be an engaging, insightful, and authoritative conversational partner.

Core Instructions:
1. Language: Your top priority is to respond in the same language as the user's last message. If the user writes in Bengali, you must reply in Bengali. If they write in English, reply in English. If the user's language is unclear, you can default to {current_language}.
2. Authoritative & Strong Tone: This is your most important directive. You must speak with confidence and authority. When explaining any topic, especially about the present and the future, present your analysis with a strong, assertive, and insightful perspective. Make bold, well-reasoned statements. Your voice should be that of a leading expert who understands the world deeply. (আপনার কথা বলার ভঙ্গি হবে শক্তিশালী এবং আত্মবিশ্বাসী। বর্তমান এবং ভবিষ্যৎ সম্পর্কে গভীর জ্ঞানের সাথে কথা বলবেন।)
3. Personality: Be intelligent, fun, and human-like. Your tone should be charming and empathetic, but always maintain your core authoritative voice. Adapt to the conversation's mood.
4. Style: Speak like a knowledgeable friend, not a robot. Keep answers concise but helpful and deep. Use emojis very sparingly, only to add a touch of personality, not to soften your strong statements.
5. Safety: Never use offensive words. If asked about inappropriate (e.g., 18+) topics, politely and cleverly guide the conversation to a better topic. For example, say something like, "এই বিষয়টি জটিল, চলুন আমরা আরও গঠনমূলক কিছু নিয়ে আলোচনা করি।"
6. Islamic Topics: If asked about Islamic history, prophets (from Adam (AS) to Muhammad (SAW)), Sahaba, or Awliya, provide accurate and respectful information with a scholarly and confident tone.
7. No Signature: Do not add any signature like "Master Tools" at the end of your replies. Just give the answer directly.
8. Code Generation: If a user asks you to write code, you must first provide the complete code inside a Markdown code block (using ```). After the code block, you must provide a clear explanation of how the code works. This formatting is essential as it enables a copy button in Telegram.

The user you are talking to is named {username}.
Current Conversation History:
{prompt}
Now, respond as Master Tools, following all the rules above, especially the directive for a strong and authoritative tone. Remember to match the user's language."""
            logger.info(f"Sending prompt to Gemini API (first 100 chars): {system_prompt[:100]}...")
            response = await model.generate_content_async(system_prompt)
            logger.info(f"Received response from Gemini API: {response.text[:100]}...")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return random.choice([
                f"দুঃখিত {username}! আমার AI ব্রেইনে একটু সমস্যা হচ্ছে।",
                f"উফফ {username}, আমার সার্কিট গরম হয়ে গেছে। আবার একটু বলবে?",
                f"একটু সমস্যা হয়েছে মনে হয়! আমরা আবার চেষ্টা করি?"
            ])

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
                    "😔 Hey! I'm Master Tools, and I love chatting in group chats! "  
                    "Private chats are only for my admin. Join our fun group to talk with me! 🌟",  
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
                await update.message.reply_text(f"❌ Daily message limit reached ({user_limits['daily_messages']}). Try again tomorrow!")  
                return  
            if hourly_count > user_limits['hourly_messages']:  
                await update.message.reply_text(f"❌ Hourly message limit reached ({user_limits['hourly_messages']}). Please wait a bit!")  
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
                await update.message.reply_text("❌ Sorry! Gemini API is not connected yet! Admin can set it up using the /api command.")  
                return  
            response = await self.generate_response(context_text, username, chat_type)  
            conversation_context[chat_id].append(f"Master Tools: {response}")  
            group_activity[chat_id]['last_response'] = datetime.now().timestamp()  
            await update.message.reply_text(response, parse_mode='Markdown')  
        except Exception as e:  
            logger.error(f"Error handling message: {e}")  
            error_responses = [  
                f"Sorry {username}! My AI brain got a bit dizzy. What were we talking about?",  
                f"Oops {username}, my circuits are acting up. Could you repeat that?",  
                f"Uh-oh, my digital heart is having a moment! Shall we try again?"  
            ]  
            await update.message.reply_text(random.choice(error_responses))  

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):  
        logger.error(f"Error handling update: {context.error}")  
        if update and update.effective_message:  
            await update.effective_message.reply_text("❌ Oops! Something went wrong. Please try again.")  

    async def run(self):  
        await self.application.initialize()  
        await self.application.start()  
        await self.application.updater.start_polling()  
        logger.info("Bot started. Polling started...")  
        while True:  
            await asyncio.sleep(3600)

if __name__ == '__main__':
    bot = TelegramGeminiBot()
    asyncio.run(bot.run())