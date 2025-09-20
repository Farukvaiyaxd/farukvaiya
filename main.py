import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', ''8380869007:AAEb1oevYkGl_z1PfXhUiuNMmH9Gg9aBbI4)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Can be set via environment or /api command
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '7960622720'))  # Set your Telegram user ID here
PORT = int(os.getenv('PORT', 8000))

# Global variables for dynamic API key management
current_gemini_api_key = GEMINI_API_KEY
model = None

def initialize_gemini_model(api_key):
    """Initialize Gemini model with the provided API key"""
    global model, current_gemini_api_key
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        current_gemini_api_key = api_key
        return True, "✅ Gemini API configured successfully!"
    except Exception as e:
        return False, f"❌ Error configuring Gemini API: {str(e)}"

# Initialize Gemini if API key is available
if GEMINI_API_KEY:
    success, message = initialize_gemini_model(GEMINI_API_KEY)
    if success:
        logger.info("Gemini API initialized from environment variable")
    else:
        logger.error(f"Failed to initialize Gemini API: {message}")
else:
    logger.warning("GEMINI_API_KEY not set. Use /api command to configure.")

# Store conversation context for each chat
conversation_context = {}

class TelegramGeminiBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Set up command and message handlers"""
        # Commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("api", self.api_command))
        self.application.add_handler(CommandHandler("setadmin", self.setadmin_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 Welcome to LemuX Cats Bot!

I'm powered by Google's Gemini AI and ready to chat with you!

Commands:
/start - Show this welcome message
/help - Get help and usage information
/clear - Clear conversation history
/status - Check bot status
/api <key> - Set Gemini API key (admin only)
/setadmin - Set yourself as admin (first time only)

Just send me any message and I'll respond using AI!
        """
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🆘 Help & Commands:

/start - Show welcome message
/help - Show this help message
/clear - Clear your conversation history
/status - Check if the bot is working
/api <key> - Set Gemini API key (admin only)
/setadmin - Set yourself as admin (first time use)

💬 How to use:
- Just send me any text message and I'll respond
- I can answer questions, help with tasks, have conversations
- In groups, reply to my messages or mention me
- I remember our conversation context until you use /clear

⚡ Powered by Google Gemini AI
        """
        await update.message.reply_text(help_message)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        chat_id = update.effective_chat.id
        if chat_id in conversation_context:
            del conversation_context[chat_id]
        await update.message.reply_text("🧹 Conversation history cleared! Starting fresh.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        global current_gemini_api_key, model
        
        api_status = "✅ Connected" if current_gemini_api_key and model else "❌ Not configured"
        api_key_display = f"...{current_gemini_api_key[-8:]}" if current_gemini_api_key else "Not set"
        
        status_message = f"""
🟢 Bot Status: Online
🤖 Model: Gemini 1.5 Flash
🔑 API Status: {api_status}
🔐 API Key: {api_key_display}
⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💭 Active Conversations: {len(conversation_context)}
👑 Admin ID: {ADMIN_USER_ID if ADMIN_USER_ID != 0 else 'Not set'}

✅ All systems operational!
        """
        await update.message.reply_text(status_message)

    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setadmin command - allows first user to become admin"""
        global ADMIN_USER_ID
        
        user_id = update.effective_user.id
        
        if ADMIN_USER_ID == 0:
            ADMIN_USER_ID = user_id
            await update.message.reply_text(f"👑 You have been set as the bot admin!\nYour User ID: {user_id}")
            logger.info(f"Admin set to user ID: {user_id}")
        else:
            if user_id == ADMIN_USER_ID:
                await update.message.reply_text(f"👑 You are already the admin!\nYour User ID: {user_id}")
            else:
                await update.message.reply_text("❌ Admin is already set. Only the current admin can manage the bot.")

    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /api command to set Gemini API key"""
        global current_gemini_api_key, model
        
        user_id = update.effective_user.id
        
        # Check if user is admin
        if ADMIN_USER_ID == 0:
            await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            return
            
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        # Check if API key is provided
        if not context.args:
            await update.message.reply_text("""
❌ Please provide an API key.

Usage: `/api your_gemini_api_key_here`

To get a Gemini API key:
1. Visit https://makersuite.google.com/app/apikey
2. Create a new API key
3. Use the command: /api YOUR_API_KEY

⚠️ The message will be deleted after setting the API key for security.
            """, parse_mode='Markdown')
            return

        api_key = ' '.join(context.args)
        
        # Validate API key format (basic check)
        if len(api_key) < 20 or not api_key.startswith('AI'):
            await update.message.reply_text("❌ Invalid API key format. Gemini API keys usually start with 'AI' and are longer than 20 characters.")
            return

        # Try to initialize Gemini with the new API key
        success, message = initialize_gemini_model(api_key)
        
        # Delete the command message for security
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass  # Ignore if deletion fails
        
        if success:
            await update.effective_chat.send_message(f"✅ Gemini API key updated successfully!\n🔑 Key: ...{api_key[-8:]}")
            logger.info(f"Gemini API key updated by admin {user_id}")
        else:
            await update.effective_chat.send_message(f"❌ Failed to set API key: {message}")
            logger.error(f"Failed to set API key: {message}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        try:
            chat_id = update.effective_chat.id
            user_message = update.message.text
            
            # Check if this is a group chat and if the bot is mentioned or replied to
            if update.effective_chat.type in ['group', 'supergroup']:
                bot_username = context.bot.username
                is_reply_to_bot = (update.message.reply_to_message and 
                                 update.message.reply_to_message.from_user.id == context.bot.id)
                is_mentioned = f"@{bot_username}" in user_message
                
                if not (is_reply_to_bot or is_mentioned):
                    return  # Don't respond to group messages unless mentioned or replied to

            # Send typing action
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")

            # Get or create conversation context
            if chat_id not in conversation_context:
                conversation_context[chat_id] = []

            # Add user message to context
            conversation_context[chat_id].append(f"User: {user_message}")

            # Keep only last 10 messages for context (to avoid token limits)
            if len(conversation_context[chat_id]) > 20:
                conversation_context[chat_id] = conversation_context[chat_id][-20:]

            # Prepare context for Gemini
            context_text = "\n".join(conversation_context[chat_id])
            
            # Generate response using Gemini
            if current_gemini_api_key and model:
                response = await self.generate_gemini_response(context_text)
            else:
                response = "❌ Gemini API is not configured. Admin can use /api command to set the API key."

            # Add bot response to context
            conversation_context[chat_id].append(f"Assistant: {response}")

            # Send response
            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ Sorry, I encountered an error processing your message. Please try again.")

    async def generate_gemini_response(self, prompt):
        """Generate response using Gemini API"""
        try:
            # Add system instruction for better responses
            full_prompt = f"""You are a helpful AI assistant in a Telegram chat. Be friendly, conversational, and helpful. 

Conversation history:
{prompt}

Respond naturally to the latest user message. Keep responses concise but informative."""

            response = model.generate_content(full_prompt)
            return response.text
        
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            return "❌ Sorry, I'm having trouble generating a response right now. Please try again in a moment."

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")

    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Bot...")
        
        # For Railway deployment, we'll use polling
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not provided!")
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
