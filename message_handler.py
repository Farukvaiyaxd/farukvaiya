"""
Message handler module for processing regular messages
"""

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import logging
import random
from database import db
from gemini_service import gemini_service
from response_logic import response_logic

logger = logging.getLogger(__name__)

class MessageHandler:
    def __init__(self):
        pass
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        try:
            chat_id = update.effective_chat.id
            user_message = update.message.text
            chat_type = update.effective_chat.type
            username = update.effective_user.first_name or "User"
            
            # Initialize group activity tracking
            db.init_group_activity(chat_id)
            
            # Determine if bot should respond
            should_respond = self._should_respond_to_message(update, context, user_message, chat_type)
            
            if not should_respond:
                return  # Skip this message
            
            # Send typing action
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            # Add user message to context
            db.add_message_to_context(chat_id, f"{username}: {user_message}")
            
            # Generate response
            response = await self._generate_response(chat_id, username, chat_type)
            
            # Add bot response to context
            current_char = db.get_character_for_chat(chat_id)
            db.add_message_to_context(chat_id, f"{current_char['name']}: {response}")
            
            # Update last response time
            db.update_last_response_time(chat_id, datetime.now().timestamp())
            
            # Send response
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(self._get_error_response())
    
    def _should_respond_to_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 user_message: str, chat_type: str) -> bool:
        """Determine if bot should respond to this message"""
        chat_id = update.effective_chat.id
        
        # Check for mentions and replies in groups
        is_mentioned = False
        is_reply_to_bot = False
        
        if chat_type in ['group', 'supergroup']:
            bot_username = context.bot.username
            is_reply_to_bot = (update.message.reply_to_message and 
                             update.message.reply_to_message.from_user.id == context.bot.id)
            is_mentioned = f"@{bot_username}" in user_message if bot_username else False
        
        return response_logic.should_respond_to_message(
            chat_id, user_message, chat_type, is_mentioned, is_reply_to_bot
        )
    
    async def _generate_response(self, chat_id: int, username: str, chat_type: str) -> str:
        """Generate AI response for the message"""
        if gemini_service.is_configured():
            # Get conversation context
            context_messages = db.get_conversation_context(chat_id)
            context_text = "\n".join(context_messages)
            
            return await gemini_service.generate_response(chat_id, context_text, username, chat_type)
        else:
            return "❌ Oops! My AI brain isn't connected yet! Admin can use /api command to set me up! 😅"
    
    def _get_error_response(self) -> str:
        """Get random error response"""
        error_responses = [
            "Oops! Something went wrong in my digital brain! 😅 Try again?",
            "Aw, I had a little glitch there! 🤖💫 What were you saying?",
            "Sorry! My circuits got tangled for a sec! 😵‍💫 Can you repeat that?",
            "Eek! Technical difficulties! 🛠️💕 Let's try that again!"
        ]
        return random.choice(error_responses)

# Global message handler instance
message_handler = MessageHandler()