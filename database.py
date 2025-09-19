"""
Database module for storing bot data
In production, this could be replaced with Redis, PostgreSQL, or MongoDB
"""

from config import DEFAULT_CHARACTER, DEFAULT_MODEL
from typing import Dict, Any, Optional

class BotDatabase:
    def __init__(self):
        # In-memory storage (replace with persistent storage in production)
        self.conversation_context = {}
        self.group_activity = {}
        self.group_models = {}
        self.group_characters = {}
        self.current_gemini_api_key = None
        self.admin_user_id = 0
    
    # Conversation Context Management
    def add_message_to_context(self, chat_id: int, message: str):
        """Add a message to conversation context"""
        if chat_id not in self.conversation_context:
            self.conversation_context[chat_id] = []
        
        self.conversation_context[chat_id].append(message)
        
        # Keep only last 20 messages for context
        if len(self.conversation_context[chat_id]) > 20:
            self.conversation_context[chat_id] = self.conversation_context[chat_id][-20:]
    
    def get_conversation_context(self, chat_id: int) -> list:
        """Get conversation context for a chat"""
        return self.conversation_context.get(chat_id, [])
    
    def clear_conversation_context(self, chat_id: int):
        """Clear conversation context for a chat"""
        if chat_id in self.conversation_context:
            del self.conversation_context[chat_id]
    
    def get_context_count(self) -> int:
        """Get total number of active conversations"""
        return len(self.conversation_context)
    
    # Group Activity Management
    def init_group_activity(self, chat_id: int):
        """Initialize group activity tracking"""
        if chat_id not in self.group_activity:
            self.group_activity[chat_id] = {'auto_mode': True, 'last_response': 0}
    
    def set_auto_mode(self, chat_id: int, enabled: bool):
        """Set auto-response mode for a group"""
        self.init_group_activity(chat_id)
        self.group_activity[chat_id]['auto_mode'] = enabled
    
    def get_auto_mode(self, chat_id: int) -> bool:
        """Get auto-response mode status"""
        return self.group_activity.get(chat_id, {}).get('auto_mode', True)
    
    def update_last_response_time(self, chat_id: int, timestamp: float):
        """Update last response time"""
        self.init_group_activity(chat_id)
        self.group_activity[chat_id]['last_response'] = timestamp
    
    # Model Management
    def set_group_model(self, chat_id: int, model_id: str):
        """Set AI model for a specific group"""
        self.group_models[chat_id] = model_id
    
    def get_group_model_id(self, chat_id: int) -> str:
        """Get model ID for a specific group"""
        return self.group_models.get(chat_id, DEFAULT_MODEL)
    
    # Character Management
    def set_character_setting(self, chat_id: int, setting: str, value: str):
        """Set a character setting for a specific chat"""
        if chat_id not in self.group_characters:
            self.group_characters[chat_id] = DEFAULT_CHARACTER.copy()
        
        self.group_characters[chat_id][setting] = value
    
    def get_character_for_chat(self, chat_id: int) -> Dict[str, str]:
        """Get character settings for a specific chat"""
        return self.group_characters.get(chat_id, DEFAULT_CHARACTER.copy())
    
    def reset_character(self, chat_id: int):
        """Reset character to default settings"""
        self.group_characters[chat_id] = DEFAULT_CHARACTER.copy()
    
    # API Key Management
    def set_api_key(self, api_key: str):
        """Set Gemini API key"""
        self.current_gemini_api_key = api_key
    
    def get_api_key(self) -> Optional[str]:
        """Get current API key"""
        return self.current_gemini_api_key
    
    # Admin Management
    def set_admin(self, user_id: int):
        """Set admin user ID"""
        self.admin_user_id = user_id
    
    def get_admin_id(self) -> int:
        """Get admin user ID"""
        return self.admin_user_id
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return self.admin_user_id != 0 and user_id == self.admin_user_id

# Global database instance
db = BotDatabase()