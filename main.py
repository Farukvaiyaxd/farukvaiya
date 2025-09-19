"""
Main entry point for the Leyana Telegram Bot
Modular architecture with separate concerns
"""

import logging
from config import TELEGRAM_BOT_TOKEN, GEMINI_API_KEY
from database import db
from gemini_service import gemini_service
from api_manager import api_manager
from bot import LeyanaBot

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def initialize_bot():
    """Initialize bot with environment variables"""
    # Initialize API manager with environment API key if available
    if GEMINI_API_KEY:
        success, message = api_manager.add_api_key(GEMINI_API_KEY, "Environment Variable")
        if success:
            logger.info("Gemini API initialized from environment variable")
        else:
            logger.error(f"Failed to initialize Gemini API: {message}")
    else:
        logger.warning("GEMINI_API_KEY not set. Use /setadmin and /addapi commands to set up.")

def main():
    """Main function"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not provided!")
        return

    logger.info("Initializing Leyana Bot...")
    
    # Initialize components
    initialize_bot()
    
    # Create and start bot
    bot = LeyanaBot()
    bot.run()

if __name__ == '__main__':
    main()