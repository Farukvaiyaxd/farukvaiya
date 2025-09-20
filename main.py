import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio
from datetime import datetime, timedelta
import random
import re
import json

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
vision_model = None

def initialize_gemini_model(api_key):
    """Initialize Gemini model with the provided API key"""
    global model, vision_model, current_gemini_api_key
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        current_gemini_api_key = api_key
        return True, "জেমিনি এপিআই সফলভাবে কনফিগার করা হয়েছে!"
    except Exception as e:
        return False, f"ত্রুটি: জেমিনি এপিআই কনফিগার করতে সমস্যা: {str(e)}"

# Initialize Gemini if API key is available
if GEMINI_API_KEY:
    success, message = initialize_gemini_model(GEMINI_API_KEY)
    if success:
        logger.info("Gemini API initialized from environment variable")
    else:
        logger.error(f"Failed to initialize Gemini API: {message}")
else:
    logger.warning("GEMINI_API_KEY not set. Use /api command to configure.")

# Store data
conversation_context = {}
group_activity = {}
user_data = {}

# Response probability and triggers
RESPONSE_PROBABILITY = {
    'question_words': 0.9,
    'emotion_words': 0.8,
    'greeting_words': 0.7,
    'random_chat': 0.3,
    'keywords': 0.8
}

TRIGGER_PATTERNS = {
    'questions': ['what', 'how', 'why', 'when', 'where', 'who', 'can', 'will', 'should', '?', 'কি', 'কেন', 'কিভাবে'],
    'emotions': ['sad', 'happy', 'angry', 'excited', 'tired', 'bored', 'lonely', 'love', 'hate', 'খুশি', 'দুঃখিত',
                 '😭', '😂', '😍', '😡', '😴', '🥱', '💕', '❤️', '💔', '😢', '😊'],
    'greetings': ['hello', 'hi', 'hey', 'good morning', 'good night', 'bye', 'goodbye', 'আসসালামু', 'হ্যালো'],
    'keywords': ['bot', 'ai', 'gemini', 'cute', 'beautiful', 'smart', 'funny', 'help', 'thanks', 'ধন্যবাদ'],
    'bangla': ['বাংলা', 'বাংলায়', 'bengali', 'translate', 'অনুবাদ']
}

class TelegramGeminiBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Set up handlers"""
        # Basic commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("api", self.api_command))
        self.application.add_handler(CommandHandler("setadmin", self.setadmin_command))
        self.application.add_handler(CommandHandler("automode", self.automode_command))
        
        # New features
        self.application.add_handler(CommandHandler("translate", self.translate_command))
        self.application.add_handler(CommandHandler("image", self.image_command))
        self.application.add_handler(CommandHandler("joke", self.joke_command))
        self.application.add_handler(CommandHandler("story", self.story_command))
        self.application.add_handler(CommandHandler("math", self.math_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        self.application.add_handler(CommandHandler("remind", self.remind_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command with menu"""
        keyboard = [
            [InlineKeyboardButton("সাহায্য", callback_data="help"),
             InlineKeyboardButton("ফিচার", callback_data="features")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = """
হায়! আমি I Master Tools, তোমার এআই সঙ্গী! 

নতুন ফিচার:
🔤 অনুবাদ (/translate)  
📸 ছবি বিশ্লেষণ (/image)
🎭 জোক ও গল্প
🧮 গণিত সমাধান
🌤️ আবহাওয়ার তথ্য
⏰ রিমাইন্ডার

গ্রুপে আমাকে মেনশন করে কথা শুরু করো! 💕
        """
        # Add custom message with Telegram button
        custom_message = """
আমাদের দারুণ কমিউনিটিতে যোগ দাও!  
আমার সাথে এবং অন্যদের সাথে আমাদের প্রাণবন্ত টেলিগ্রাম গ্রুপে চ্যাট করো! 💬✨  
নিচে ক্লিক করে মজায় যোগ দাও! 😊
        """
        join_button = [[InlineKeyboardButton("VPSHUB_BD_CHAT-এ যোগ দাও", url="https://t.me/VPSHUB_BD_CHAT")]]
        custom_reply_markup = InlineKeyboardMarkup(join_button)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        await update.message.reply_text(custom_message, reply_markup=custom_reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_message = """
কমান্ড:

বেসিক: /start /help /clear /status
অ্যাডমিন: /api /setadmin /automode

ফিচার:
/translate <টেক্সট> - টেক্সট অনুবাদ
/image - ছবি বিশ্লেষণ  
/joke - র‍্যান্ডম জোক
/story <টপিক> - গল্প তৈরি
/math <প্রবলেম> - গণিত সমাধান
/weather <শহর> - আবহাওয়ার তথ্য
/remind <মিনিট> <টেক্সট> - রিমাইন্ডার সেট

গ্রুপে আমাকে মেনশন করে চ্যাট করো! 💕
        """
        await update.message.reply_text(help_message)

    async def translate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Smart mention translation system"""
        if not current_gemini_api_key or not model:
            await update.message.reply_text("এপিআই কী প্রয়োজন! /api কমান্ড ব্যবহার করো")
            return

        # Check if there are mentions in the command
        entities = update.message.entities or []
        mentions = []
        
        for entity in entities:
            if entity.type == "mention":
                mention_text = update.message.text[entity.offset:entity.offset + entity.length]
                mentions.append(mention_text)
            elif entity.type == "text_mention":
                user = entity.user
                username = f"@{user.username}" if user.username else user.first_name
                mentions.append(username)

        # Method 1: Reply to message
        if update.message.reply_to_message and update.message.reply_to_message.text:
            text_to_translate = update.message.reply_to_message.text
            original_user = update.message.reply_to_message.from_user
            target_mention = f"@{original_user.username}" if original_user.username else original_user.first_name
            
        # Method 2: Mention + text in same message  
        elif mentions and len(update.message.text.split()) > 2:
            # Extract text after mentions and /translate command
            words = update.message.text.split()
            # Find where actual text starts (after /translate and mentions)
            text_start_idx = 1  # Skip /translate
            for word in words[1:]:
                if word.startswith('@') or word in mentions:
                    text_start_idx += 1
                else:
                    break
            
            if text_start_idx < len(words):
                text_to_translate = ' '.join(words[text_start_idx:])
                target_mention = mentions[0] if mentions else None
            else:
                await update.message.reply_text("মেনশনের পরে টেক্সট দাও!")
                return
                
        # Method 3: Direct text only
        elif context.args:
            text_to_translate = ' '.join(context.args)
            target_mention = None
            
        else:
            await update.message.reply_text("""
অনুবাদের পদ্ধতি:

১. রিপ্লাই পদ্ধতি:
যেকোনো মেসেজে রিপ্লাই করে `/translate`

২. মেনশন পদ্ধতি:
`/translate @username হ্যালো, তুমি কেমন আছো?`
`/translate @username আমি ভালো আছি`

৩. সরাসরি পদ্ধতি:
`/translate হ্যালো ওয়ার্ল্ড`

আমি স্মার্টভাবে ভাষা সনাক্ত করে অনুবাদ করব! 💕
            """)
            return

        try:
            # Smart translation with language detection
            prompt = f"""
এই টেক্সটটি স্মার্টভাবে অনুবাদ করো:

টেক্সট: "{text_to_translate}"

নিয়ম:
- যদি বাংলা হয় → ইংরেজি
- যদি ইংরেজি হয় → বাংলা
- অন্য ভাষা হলে → ইংরেজি এবং বাংলা উভয়
- মূল টোন এবং অর্থ অক্ষুণ্ণ রাখো
- স্বাভাবিক এবং কথোপকথনের মতো হবে

অতিরিক্ত ফরম্যাটিং ছাড়া পরিষ্কার অনুবাদ দাও।
"""
            
            response = model.generate_content(prompt)
            translation_result = response.text.strip()
            
            # Format final message
            if target_mention:
                final_message = f"{target_mention}\n\nঅনুবাদ:\n{translation_result}"
            else:
                final_message = f"অনুবাদ:\n{translation_result}"
                
            await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n{final_message}")
                
        except Exception as e:
            await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nঅনুবাদ ব্যর্থ: {str(e)}")
            
        # Clean up command message
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, 
                message_id=update.message.message_id
            )
        except:
            pass

    async def image_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Image analysis help"""
        await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nআমাকে যেকোনো ছবি পাঠাও, আমি তা বিশ্লেষণ করব! 💕")

    async def joke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate jokes"""
        if current_gemini_api_key and model:
            try:
                response = model.generate_content("ইমোজি সহ একটি ছোট মজার জোক বলো")
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n😄 {response.text}")
            except:
                jokes = ["😄 রোবট কখনো প্যানিক করে না কেন? তাদের সার্কিট ভালো! 🤖", 
                        "😂 কম্পিউটারের প্রিয় স্ন্যাক কী? মাইক্রোচিপ! 💾"]
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n{random.choice(jokes)}")
        else:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nজোকের জন্য এপিআই প্রয়োজন!")

    async def story_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate short stories"""
        topic = ' '.join(context.args) if context.args else "বন্ধুত্ব"
        
        if current_gemini_api_key and model:
            try:
                prompt = f"{topic} নিয়ে ইমোজি সহ ১০০ শব্দের একটি ছোট গল্প লেখো"
                response = model.generate_content(prompt)
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nগল্প:\n\n{response.text}")
            except Exception as e:
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nত্রুটি: {str(e)}")
        else:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nগল্পের জন্য এপিআই প্রয়োজন!")

    async def math_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Solve math problems"""
        if not context.args:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nব্যবহার: /math <প্রবলেম>\nউদাহরণ: /math 25 + 17 * 3")
            return

        problem = ' '.join(context.args)
        
        if current_gemini_api_key and model:
            try:
                prompt = f"ধাপে ধাপে এই গণিত সমাধান করো: {problem}"
                response = model.generate_content(prompt)
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nসমাধান:\n{response.text}")
            except Exception as e:
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nত্রুটি: {str(e)}")
        else:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nগণিতের জন্য এপিআই প্রয়োজন!")

    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Weather info"""
        if not context.args:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nব্যবহার: /weather <শহর>\nউদাহরণ: /weather ঢাকা")
            return

        city = ' '.join(context.args)
        
        if current_gemini_api_key and model:
            try:
                prompt = f"{city} এর জন্য আবহাওয়ার পরামর্শ এবং সাধারণ তথ্য ইমোজি সহ দাও"
                response = model.generate_content(prompt)
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n{city} এর আবহাওয়া:\n{response.text}")
            except Exception as e:
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nত্রুটি: {str(e)}")
        else:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nআবহাওয়ার জন্য এপিআই প্রয়োজন!")

    async def remind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set reminders"""
        if len(context.args) < 2:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nব্যবহার: /remind <মিনিট> <মেসেজ>\nউদাহরণ: /remind 30 ওষুধ খাও")
            return

        try:
            minutes = int(context.args[0])
            message = ' '.join(context.args[1:])
            
            await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n{minutes} মিনিটের জন্য রিমাইন্ডার সেট করা হয়েছে: {message}")
            
            # Schedule reminder
            context.job_queue.run_once(
                self.send_reminder,
                minutes * 60,
                data={'chat_id': update.effective_chat.id, 'message': message, 'user': update.effective_user.first_name}
            )
        except ValueError:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nসঠিক মিনিটের সংখ্যা দাও!")

    async def send_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Send reminder"""
        data = context.job.data
        try:
            await context.bot.send_message(
                chat_id=data['chat_id'],
                text=f"এইআই থেকে রিপ্লাই আসবে\n{data['user']} এর জন্য রিমাইন্ডার: {data['message']} 💕"
            )
        except Exception as e:
            logger.error(f"Reminder failed: {e}")

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo analysis"""
        try:
            if update.effective_chat.type == 'private':
                join_button = [[InlineKeyboardButton("VPSHUB_BD_CHAT-এ যোগ দাও", url="https://t.me/VPSHUB_BD_CHAT")]]
                reply_markup = InlineKeyboardMarkup(join_button)
                await update.message.reply_text(
                    "হায়! আমি ছবি বিশ্লেষণ করতে পারি, কিন্তু চলো আমাদের দারুণ গ্রুপে কথা বলি! সেখানে ছবি শেয়ার করো! 💬✨",
                    reply_markup=reply_markup
                )
                return

            if not current_gemini_api_key or not vision_model:
                await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nছবি বিশ্লেষণের জন্য এপিআই কী প্রয়োজন! 📸")
                return

            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Get photo
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            
            # Download and process
            from io import BytesIO
            photo_bytes = BytesIO()
            await photo_file.download_to_memory(photo_bytes)
            photo_bytes.seek(0)
            
            # Analyze with Gemini Vision
            try:
                # Convert to format Gemini can use
                import PIL.Image
                image = PIL.Image.open(photo_bytes)
                
                prompt = "এই ছবিটি বন্ধুত্বপূর্ণভাবে বর্ণনা করো। কী দেখছ? কথোপকথনের মতো বলো এবং ইমোজি ব্যবহার করো!"
                response = vision_model.generate_content([prompt, image])
                
                await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nআমি দেখতে পাচ্ছি:\n\n{response.text}")
                
            except Exception as e:
                await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nএই ছবিটি বিশ্লেষণ করতে পারিনি। আরেকটি চেষ্টা করো! 📸💕")
                
        except Exception as e:
            logger.error(f"Photo handling error: {e}")
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nছবি প্রক্রিয়াকরণ ব্যর্থ! আবার চেষ্টা করো? 😊")

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear conversation"""
        chat_id = update.effective_chat.id
        if chat_id in conversation_context:
            del conversation_context[chat_id]
        await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nমেমোরি ক্লিয়ার করা হয়েছে! নতুন করে শুরু 💕")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot status"""
        api_status = "প্রস্তুত" if current_gemini_api_key else "কনফিগার করা হয়নি"
        chat_id = update.effective_chat.id
        auto_mode = "চালু" if group_activity.get(chat_id, {}).get('auto_mode', True) else "বন্ধ"
        
        await update.message.reply_text(f"""
এইআই থেকে রিপ্লাই আসবে
I Master Tools স্ট্যাটাস:

অনলাইন এবং প্রস্তুত!
এপিআই: {api_status}  
স্বয়ংক্রিয় রেসপন্স: {auto_mode}
সক্রিয় চ্যাট: {len(conversation_context)}
{datetime.now().strftime('%H:%M:%S')}

সব ঠিক আছে! 😊💕
        """)

    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set admin"""
        global ADMIN_USER_ID
        user_id = update.effective_user.id
        
        if ADMIN_USER_ID == 0:
            ADMIN_USER_ID = user_id
            await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nতুমি এখন অ্যাডমিন! আইডি: {user_id}")
        else:
            if user_id == ADMIN_USER_ID:
                await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nতুমি ইতিমধ্যে অ্যাডমিন!")
            else:
                await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nঅ্যাডমিন ইতিমধ্যে সেট করা হয়েছে!")

    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set API key"""
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nশুধুমাত্র অ্যাডমিন!")
            return

        if not context.args:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nব্যবহার: /api তোমার_এপিআই_কী")
            return

        api_key = ' '.join(context.args)
        success, message = initialize_gemini_model(api_key)
        
        # Delete command for security
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        await update.effective_chat.send_message(f"এইআই থেকে রিপ্লাই আসবে\n{message}")

    async def automode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Toggle auto responses"""
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nশুধুমাত্র অ্যাডমিন!")
            return

        chat_id = update.effective_chat.id
        if chat_id not in group_activity:
            group_activity[chat_id] = {'auto_mode': True}
        
        group_activity[chat_id]['auto_mode'] = not group_activity[chat_id]['auto_mode']
        status = "চালু" if group_activity[chat_id]['auto_mode'] else "বন্ধ"
        
        await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\nস্বয়ংক্রিয় রেসপন্স {status}!")

    def should_respond_to_message(self, message_text, chat_type, has_mention=False):
        """Check if should respond"""
        if chat_type == 'private':
            return False  # No responses in private chats
        
        # Only respond if mentioned or replying to bot
        if has_mention:
            return True
            
        return False  # No random responses or trigger-based responses

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            chat_id = update.effective_chat.id
            user_message = update.message.text
            chat_type = update.effective_chat.type
            
            # Block all private chat messages and redirect to group
            if chat_type == 'private':
                join_button = [[InlineKeyboardButton("VPSHUB_BD_CHAT-এ যোগ দাও", url="https://t.me/VPSHUB_BD_CHAT")]]
                reply_markup = InlineKeyboardMarkup(join_button)
                await update.message.reply_text(
                    "হায়! আমি I Master Tools, এবং আমি কথা বলতে ভালোবাসি! আমাদের দারুণ টেলিগ্রাম গ্রুপে কথা বলি! সেখানে যোগ দাও মজার কথোপকথনের জন্য! 💬✨",
                    reply_markup=reply_markup
                )
                return
            
            # Check for mentions in the message
            entities = update.message.entities or []
            has_bot_mention = False
            has_any_mention = False
            
            for entity in entities:
                if entity.type == "mention":
                    mention_text = update.message.text[entity.offset:entity.offset + entity.length]
                    if mention_text == f"@{context.bot.username}":
                        has_bot_mention = True
                    has_any_mention = True
                elif entity.type == "text_mention":
                    has_any_mention = True
                    if entity.user.id == context.bot.id:
                        has_bot_mention = True
            
            # Group response logic
            if chat_type in ['group', 'supergroup']:
                is_reply = (update.message.reply_to_message and 
                           update.message.reply_to_message.from_user.id == context.bot.id)
                
                # Only respond if:
                # 1. Bot is mentioned
                # 2. Reply to bot
                should_respond = has_bot_mention or is_reply
                
                if not should_respond:
                    return
                    
                # Check auto mode
                if not group_activity.get(chat_id, {}).get('auto_mode', True):
                    # Still respond to direct mentions/replies even if auto mode is off
                    if not (has_bot_mention or is_reply):
                        return

            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Get context
            if chat_id not in conversation_context:
                conversation_context[chat_id] = []

            username = update.effective_user.first_name or "ইউজার"
            conversation_context[chat_id].append(f"{username}: {user_message}")

            # Keep last 20 messages
            if len(conversation_context[chat_id]) > 20:
                conversation_context[chat_id] = conversation_context[chat_id][-20:]

            context_text = "\n".join(conversation_context[chat_id])
            
            # Generate response
            if current_gemini_api_key and model:
                # Add context about mentions for better responses
                mention_context = ""
                if has_any_mention and not has_bot_mention:
                    mention_context = " (ইউজার এই মেসেজে কাউকে মেনশন করেছে)"
                elif has_bot_mention:
                    mention_context = " (ইউজার তোমাকে সরাসরি মেনশন করেছে)"
                    
                response = await self.generate_gemini_response(
                    context_text + mention_context, username, chat_type
                )
            else:
                response = "আমার এআই মস্তিষ্ক সেটআপ প্রয়োজন! অ্যাডমিন /api কমান্ড ব্যবহার করো! 😅"

            conversation_context[chat_id].append(f"I Master Tools: {response}")
            await update.message.reply_text(f"এইআই থেকে রিপ্লাই আসবে\n{response}")

        except Exception as e:
            logger.error(f"Message error: {e}")
            await update.message.reply_text("এইআই থেকে রিপ্লাই আসবে\nওহো! কিছু ভুল হয়েছে! 😅 আবার চেষ্টা করো?")

    async def generate_gemini_response(self, prompt, username="ইউজার", chat_type="private"):
        """Generate AI response"""
        try:
            system_prompt = f"""তুমি I Master Tools, একটি বন্ধুত্বপূর্ণ এআই। শুধুমাত্র বাংলায় কথা বলো, ইউজার যেকোনো ভাষায় কথা বললেও। রেসপন্স ছোট এবং মিষ্টি রাখো।

বৈশিষ্ট্য: বন্ধুত্বপূর্ণ, মজার, আবেগপ্রবণ, স্বাভাবিকভাবে ইমোজি ব্যবহার করো 💕
চ্যাটের ধরন: {'গ্রুপ' if chat_type in ['group', 'supergroup'] else 'প্রাইভেট'}
ইউজার: {username}

কথোপকথন:
{prompt}

I Master Tools হিসেবে স্বাভাবিকভাবে রেসপন্স করো! আকর্ষণীয় কিন্তু সংক্ষিপ্ত হও।"""

            response = model.generate_content(system_prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"AI response error: {e}")
            responses = [
                f"দুঃখিত {username}! মস্তিষ্কে ত্রুটি 😅 আবার কী বলছিলে?",
                "ওহো! মাথা ঘুরে গেছে 🤖💫 আবার বলো?",
                "টেকনিক্যাল সমস্যা! 🛠️✨ আরেকবার চেষ্টা করো?"
            ]
            return random.choice(responses)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "help":
            await query.message.edit_text("""
এইআই থেকে রিপ্লাই আসবে
দ্রুত সাহায্য:

/translate - টেক্সট অনুবাদ
/image - ছবি বিশ্লেষণ  
/joke - জোক শোনো
/story - গল্প তৈরি
/math - গণিত সমাধান
/weather - আবহাওয়ার তথ্য
/remind - রিমাইন্ডার সেট

গ্রুপে আমাকে মেনশন করে কথা বলো! 💕
            """)
        elif query.data == "features":
            await query.message.edit_text("""
এইআই থেকে রিপ্লাই আসবে
আমার ফিচার:

বাংলা↔ইংরেজি অনুবাদ
এআই দিয়ে ছবি বিশ্লেষণ
জোক ও বিনোদন  
গল্প তৈরি
গণিত সমাধানকারী
আবহাওয়ার তথ্য
স্মার্ট রিমাইন্ডার
স্বাভাবিক কথোপকথন

আমি সবসময় শিখছি! 💕
            """)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update error: {context.error}")

    def run(self):
        """Start bot"""
        logger.info("Starting bot...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("No bot token!")
        return

    logger.info("Bot starting...")
    bot = TelegramGeminiBot()
    bot.run()

if __name__ == '__main__':
    main()