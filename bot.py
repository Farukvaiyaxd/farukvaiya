"""
Main bot class that orchestrates all components
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from config import TELEGRAM_BOT_TOKEN
from commands import command_handlers
from message_handler import message_handler

logger = logging.getLogger(__name__)

class LeyanaBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", command_handlers.start_command))
        self.application.add_handler(CommandHandler("help", command_handlers.help_command))
        self.application.add_handler(CommandHandler("clear", command_handlers.clear_command))
        self.application.add_handler(CommandHandler("status", command_handlers.status_command))
        self.application.add_handler(CommandHandler("api", command_handlers.api_command))
        self.application.add_handler(CommandHandler("setadmin", command_handlers.setadmin_command))
        self.application.add_handler(CommandHandler("automode", command_handlers.automode_command))
        self.application.add_handler(CommandHandler("model", command_handlers.model_command))
        self.application.add_handler(CommandHandler("character", command_handlers.character_command))
        self.application.add_handler(CommandHandler("addapi", command_handlers.addapi_command))
        self.application.add_handler(CommandHandler("removeapi", command_handlers.removeapi_command))
        self.application.add_handler(CommandHandler("listapis", command_handlers.listapis_command))
        self.application.add_handler(CommandHandler("apistat", command_handlers.apistat_command))
        self.application.add_handler(CommandHandler("toggleapi", command_handlers.toggleapi_command))
        
        # Message handlers
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_message)
        )
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Leyana Bot...")
        logger.info("Bot is ready to chat!")
        
        # Use polling for Railway deployment
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )