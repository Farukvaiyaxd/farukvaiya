"""
Utility functions for the bot
"""

from datetime import datetime
import re
from typing import Optional

def format_timestamp(timestamp: float) -> str:
    """Format timestamp for display"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def is_valid_api_key(api_key: str) -> tuple[bool, str]:
    """Validate Gemini API key format"""
    if not api_key:
        return False, "API key cannot be empty"
    
    if len(api_key) < 20:
        return False, "API key is too short"
    
    if not api_key.startswith('AI'):
        return False, "Gemini API keys usually start with 'AI'"
    
    return True, "Valid format"

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    # Remove any potential harmful characters
    text = re.sub(r'[<>&"]', '', text)
    return text.strip()

def get_display_name(user) -> str:
    """Get display name for user"""
    if user.first_name:
        return user.first_name
    elif user.username:
        return user.username
    else:
        return "User"

def mask_api_key(api_key: Optional[str]) -> str:
    """Mask API key for display"""
    if not api_key:
        return "Not set"
    
    if len(api_key) < 8:
        return "***"
    
    return f"...{api_key[-8:]}"

class BotStats:
    """Simple stats tracker"""
    
    def __init__(self):
        self.messages_processed = 0
        self.responses_generated = 0
        self.errors_encountered = 0
        self.start_time = datetime.now()
    
    def increment_messages(self):
        self.messages_processed += 1
    
    def increment_responses(self):
        self.responses_generated += 1
    
    def increment_errors(self):
        self.errors_encountered += 1
    
    def get_uptime(self) -> str:
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{uptime.days}d {hours}h {minutes}m {seconds}s"

# Global stats instance
bot_stats = BotStats()