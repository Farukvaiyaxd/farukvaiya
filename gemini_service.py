"""
Enhanced Gemini AI service module with multi-API support and failover
"""

import google.generativeai as genai
import logging
import random
import asyncio
from config import AVAILABLE_MODELS, DEFAULT_MODEL
from database import db
from api_manager import api_manager, APIStatus

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.model = None
    
    def initialize_model(self, api_key: str, model_name: str = 'gemini-2.5-flash') -> tuple[bool, str]:
        """Initialize Gemini model with API key and model name (legacy support)"""
        success, message = api_manager.add_api_key(api_key, "Manual Setup")
        if success:
            # Test with the specified model
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
                return True, message
            except Exception as e:
                return False, f"❌ Error testing model: {str(e)}"
        return success, message
    
    def get_model_for_chat(self, chat_id: int) -> str:
        """Get the model name for a specific chat"""
        model_id = db.get_group_model_id(chat_id)
        return AVAILABLE_MODELS[model_id]['name']
    
    async def generate_response(self, chat_id: int, prompt: str, username: str = "User", 
                              chat_type: str = "private") -> str:
        """Generate AI response with automatic API failover"""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            api_key_obj = api_manager.get_available_api()
            
            if not api_key_obj:
                return "❌ No API keys available! Admin needs to add API keys with /addapi command."
            
            try:
                # Get model and character for this chat
                model_name = self.get_model_for_chat(chat_id)
                character = db.get_character_for_chat(chat_id)
                
                # Configure and create model instance
                genai.configure(api_key=api_key_obj.key)
                chat_model = genai.GenerativeModel(model_name)
                
                # Build system prompt
                system_prompt = self._build_system_prompt(character, chat_type, prompt, username)
                
                # Generate response with timeout
                response = await asyncio.wait_for(
                    asyncio.create_task(self._generate_with_retry(chat_model, system_prompt)),
                    timeout=30
                )
                
                # Mark API as successful
                api_key_obj.mark_success()
                
                logger.info(f"Response generated using API: {api_key_obj.name}")
                return response.text
                
            except asyncio.TimeoutError:
                error_msg = "Request timeout"
                api_key_obj.mark_failure(error_msg)
                logger.warning(f"API {api_key_obj.name} timed out, trying next API")
                
            except Exception as e:
                error_msg = str(e)
                api_key_obj.mark_failure(error_msg)
                logger.error(f"API {api_key_obj.name} failed: {error_msg}")
                
                # If it's a rate limit error, put API in cooldown immediately
                if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                    api_key_obj.status = APIStatus.COOLDOWN
                    api_key_obj.cooldown_until = api_key_obj.cooldown_until + 600  # Extra 10 minutes for rate limits
            
            attempt += 1
            
            # Short delay before trying next API
            if attempt < max_attempts:
                await asyncio.sleep(1)
        
        # All APIs failed
        logger.error("All API attempts failed")
        return self._get_fallback_response(username)
    
    async def _generate_with_retry(self, model, prompt):
        """Generate response with the model"""
        return model.generate_content(prompt)
    
    def _build_system_prompt(self, character: dict, chat_type: str, prompt: str, username: str) -> str:
        """Build system prompt with character information"""
        return f"""You are {character['name']}, a {character['personality']}. You're in a Telegram {'group chat' if chat_type in ['group', 'supergroup'] else 'private chat'}.

CHARACTER TRAITS:
{character['traits']}

COMMUNICATION STYLE:
{character['style']}

BEHAVIOR PATTERNS:
{character['behavior']}

CORE PERSONALITY:
- You use emojis naturally and appropriately 💕😊✨
- You're emotionally expressive and empathetic
- You respond with enthusiasm and genuine interest
- You remember you're talking to real people and adapt to their mood
- You embody all the traits and behaviors specified above

CONVERSATION GUIDELINES:
- Keep responses conversational and natural (not too long)
- Match the energy level of the conversation
- Use appropriate emojis but don't overdo it
- Be genuinely helpful when asked questions
- If someone seems sad, be compassionate
- If someone shares good news, be excited for them
- Make jokes and be playful when the mood is light
- Remember context from the conversation
- Stay true to your character's personality and traits

Current conversation:
{prompt}

Respond as {character['name']} with the personality and traits described above. Be natural, engaging, and match the conversational tone. The user's name is {username}."""
    
    def _get_fallback_response(self, username: str) -> str:
        """Get fallback response when all APIs fail"""
        fallback_responses = [
            f"Sorry {username}! All my AI connections are having trouble right now 😅 Please try again in a moment!",
            "Oops! I'm having some technical difficulties with my brain! 🤖💫 The admin might need to check my API keys!",
            f"Aw {username}, all my AI systems are overwhelmed right now! 😔 Please be patient while they recover!",
            "My circuits are all busy right now! 🛠️✨ Try again in a few minutes please!"
        ]
        return random.choice(fallback_responses)
    
    def is_configured(self) -> bool:
        """Check if AI service has any working API keys"""
        stats = api_manager.get_api_statistics()
        return stats['total_apis'] > 0 and stats['active_apis'] > 0
    
    def get_service_status(self) -> dict:
        """Get service status information"""
        return api_manager.get_api_statistics()

# Global service instance
gemini_service = GeminiService()