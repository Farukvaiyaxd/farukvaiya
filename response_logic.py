"""
Response logic module for determining when the bot should respond
"""

import random
import logging
from config import RESPONSE_PROBABILITY, TRIGGER_PATTERNS
from database import db

logger = logging.getLogger(__name__)

class ResponseLogic:
    def __init__(self):
        pass
    
    def should_respond_to_message(self, chat_id: int, message_text: str, chat_type: str, 
                                is_mentioned: bool = False, is_reply_to_bot: bool = False) -> bool:
        """Determine if bot should respond to a message"""
        
        # Always respond in private chats
        if chat_type == 'private':
            logger.debug(f"Private chat {chat_id}: Always respond")
            return True
        
        # Always respond if mentioned or replied to
        if is_mentioned or is_reply_to_bot:
            logger.debug(f"Group chat {chat_id}: Mentioned or replied to - responding")
            return True
        
        # Check if auto mode is disabled for this group
        auto_mode_enabled = db.get_auto_mode(chat_id)
        logger.debug(f"Group chat {chat_id}: Auto mode = {auto_mode_enabled}")
        
        if not auto_mode_enabled:
            logger.debug(f"Group chat {chat_id}: Auto mode disabled - not responding")
            return False
        
        # Calculate probability-based response
        should_respond = self._calculate_response_probability(message_text)
        logger.debug(f"Group chat {chat_id}: Probability-based decision = {should_respond}")
        
        return should_respond
    
    def _calculate_response_probability(self, message_text: str) -> bool:
        """Calculate whether to respond based on message content"""
        message_lower = message_text.lower()
        
        # Always respond to questions
        if self._contains_patterns(message_lower, TRIGGER_PATTERNS['questions']):
            return random.random() < RESPONSE_PROBABILITY['question_words']
        
        # High chance for emotional content
        if self._contains_patterns(message_lower, TRIGGER_PATTERNS['emotions']):
            return random.random() < RESPONSE_PROBABILITY['emotion_words']
        
        # Good chance for greetings
        if self._contains_patterns(message_lower, TRIGGER_PATTERNS['greetings']):
            return random.random() < RESPONSE_PROBABILITY['greeting_words']
        
        # High chance for keywords
        if self._contains_patterns(message_lower, TRIGGER_PATTERNS['keywords']):
            return random.random() < RESPONSE_PROBABILITY['keywords']
        
        # Fun content
        if self._contains_patterns(message_lower, TRIGGER_PATTERNS['fun']):
            return random.random() < RESPONSE_PROBABILITY['emotion_words']
        
        # Random chance for any other message
        return random.random() < RESPONSE_PROBABILITY['random_chat']
    
    def _contains_patterns(self, text: str, patterns: list) -> bool:
        """Check if text contains any of the specified patterns"""
        return any(pattern in text for pattern in patterns)

# Global response logic instance
response_logic = ResponseLogic()