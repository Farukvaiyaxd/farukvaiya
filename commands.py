"""
Command handlers module for all bot commands
"""

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
import logging
from config import AVAILABLE_MODELS, DEFAULT_MODEL
from database import db
from gemini_service import gemini_service
from api_manager import api_manager

logger = logging.getLogger(__name__)

class CommandHandlers:
    def __init__(self):
        pass
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖💕 Hey there! I'm Leyana, your AI companion! 

I'm powered by Google's Gemini AI and I love chatting with everyone! 😊

Commands:
/start - Show this welcome message
/help - Get help and usage information  
/clear - Clear conversation history
/status - Check bot status
/api <key> - Set Gemini API key (admin only) [DEPRECATED]
/addapi <key> [name] - Add new API key (admin only)
/removeapi <id> - Remove API key (admin only)
/listapis - List all API keys (admin only)
/apistat - Show API statistics (admin only)
/toggleapi <id> - Enable/disable API key (admin only) [DEPRECATED]
/addapi <key> [name] - Add new API key (admin only)
/removeapi <id> - Remove API key (admin only)
/listapis - List all API keys (admin only)
/apistat - Show API statistics (admin only)
/toggleapi <id> - Enable/disable API key (admin only)
/setadmin - Set yourself as admin (first time only)
/automode - Toggle auto-response in groups (admin only)
/model - Choose AI model for this chat (admin only)
/character - Customize my personality for this chat (admin only)

I'll chat with you naturally in groups! I love making friends and having fun conversations! 💕✨
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🆘💕 Help & Commands:

/start - Show welcome message
/help - Show this help message
/clear - Clear your conversation history
/status - Check if I'm working properly
/api <key> - Set Gemini API key (admin only)
/setadmin - Set yourself as admin (first time use)
/automode - Toggle auto-responses in groups (admin only)
/model - Choose AI model for this chat (admin only)
/character - Customize my personality & behavior (admin only)

💬 How I work:
- I automatically join conversations in groups! 
- I respond to questions, emotions, greetings, and interesting messages
- In private chats, I always respond to everything
- I remember our conversation context until you use /clear
- I'm designed to be friendly, fun, and helpful like a real person! 

🎭 My personality:
- I'm Leyana, and my personality can be customized for each group!
- I can be funny, emotional, supportive, or whatever fits your community
- I use emojis and casual language to feel more human
- I love roleplay and creative conversations! 

🤖 Customization:
- Different groups can use different AI models for varied experiences
- Admins can customize my personality, traits, and behavior style
- Each chat gets its own unique version of me!

⚡ Powered by Google Gemini AI 💕
        """
        await update.message.reply_text(help_message)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        chat_id = update.effective_chat.id
        db.clear_conversation_context(chat_id)
        await update.message.reply_text("🧹 Conversation history cleared! Starting fresh.")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        chat_id = update.effective_chat.id
        auto_mode_status = "✅ Enabled" if db.get_auto_mode(chat_id) else "❌ Disabled"
        
        # Get current model and character for this chat
        current_model_id = db.get_group_model_id(chat_id)
        current_model_info = AVAILABLE_MODELS[current_model_id]
        current_char = db.get_character_for_chat(chat_id)
        
        # Get API statistics
        api_stats = api_manager.get_api_statistics()
        api_status = f"✅ {api_stats['active_apis']}/{api_stats['total_apis']} Active" if api_stats['active_apis'] > 0 else "❌ No Active APIs"
        
        status_message = f"""
🤖💕 {current_char['name']} Status Report:

🟢 Bot Status: Online & Ready!
👤 Character: {current_char['name']}
💫 Personality: {current_char['personality'][:50]}{"..." if len(current_char['personality']) > 50 else ""}
🤖 AI Model: {current_model_info['display']} ⚡
📝 Model Info: {current_model_info['description']}
🔑 API Status: {api_status}
📊 Success Rate: {api_stats['success_rate']:.1f}%
🎯 Auto-Response: {auto_mode_status}
⏰ Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💭 Active Conversations: {db.get_context_count()}
👑 Admin ID: {db.get_admin_id() if db.get_admin_id() != 0 else 'Not set'}

✨ I'm {current_char['name']} and I'm ready to chat! 🧠💕
        """
        await update.message.reply_text(status_message)
    
    async def setadmin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setadmin command"""
        user_id = update.effective_user.id
        
        if db.get_admin_id() == 0:
            db.set_admin(user_id)
            await update.message.reply_text(f"👑 You have been set as the bot admin!\nYour User ID: {user_id}")
            logger.info(f"Admin set to user ID: {user_id}")
        else:
            if user_id == db.get_admin_id():
                await update.message.reply_text(f"👑 You are already the admin!\nYour User ID: {user_id}")
            else:
                await update.message.reply_text("❌ Admin is already set. Only the current admin can manage the bot.")
    
    async def api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /api command"""
        user_id = update.effective_user.id
        
        # Check admin permissions
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return
        
        # Validate input
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
        
        # Validate API key format
        if len(api_key) < 20 or not api_key.startswith('AI'):
            await update.message.reply_text("❌ Invalid API key format. Gemini API keys usually start with 'AI' and are longer than 20 characters.")
            return
        
        # Try to initialize Gemini
        success, message = gemini_service.initialize_model(api_key)
        
        # Delete command message for security
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        if success:
            await update.effective_chat.send_message(f"✅ Gemini API key updated successfully!\n🔑 Key: ...{api_key[-8:]}")
            logger.info(f"Gemini API key updated by admin {user_id}")
        else:
            await update.effective_chat.send_message(f"❌ Failed to set API key: {message}")
    
    async def automode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /automode command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return
        
        # Toggle auto mode
        current_mode = db.get_auto_mode(chat_id)
        new_mode = not current_mode
        db.set_auto_mode(chat_id, new_mode)
        
        # Log the change for debugging
        logger.info(f"Auto-mode toggled for chat {chat_id}: {current_mode} -> {new_mode} by admin {user_id}")
        
        status = "enabled" if new_mode else "disabled"
        emoji = "✅" if new_mode else "❌"
        
        await update.message.reply_text(
            f"{emoji} **Auto-response mode {status} for this chat!**\n\n"
            f"🔧 **Debug Info:**\n"
            f"Chat ID: `{chat_id}`\n"
            f"Previous: {'Enabled' if current_mode else 'Disabled'}\n" 
            f"Current: {'Enabled' if new_mode else 'Disabled'}\n\n"
            f"{'I will now respond automatically to interesting messages!' if new_mode else 'I will only respond when mentioned or replied to.'}", 
            parse_mode='Markdown'
        )
    
    async def model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /model command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return
        
        # Show available models if no argument
        if not context.args:
            current_model_id = db.get_group_model_id(chat_id)
            current_model = AVAILABLE_MODELS[current_model_id]
            
            model_list = "🤖 **Available AI Models:**\n\n"
            for model_id, model_info in AVAILABLE_MODELS.items():
                emoji = "✅" if model_id == current_model_id else "⚫"
                model_list += f"{emoji} **{model_id}.** {model_info['display']}\n"
                model_list += f"   {model_info['description']}\n\n"
            
            model_list += f"**Current Model:** {current_model['display']} ✨\n\n"
            model_list += "**Usage:** `/model <number>`\n"
            model_list += "**Example:** `/model 2` (for Gemini 2.5 Flash Lite)"
            
            await update.message.reply_text(model_list, parse_mode='Markdown')
            return
        
        # Set selected model
        selected_id = context.args[0]
        
        if selected_id not in AVAILABLE_MODELS:
            await update.message.reply_text("❌ Invalid model number! Use `/model` to see available options.")
            return
        
        db.set_group_model(chat_id, selected_id)
        selected_model = AVAILABLE_MODELS[selected_id]
        
        await update.message.reply_text(
            f"✅ **Model Updated!**\n\n"
            f"🤖 **New Model:** {selected_model['display']}\n"
            f"📝 **Description:** {selected_model['description']}\n\n"
            f"I'm now using {selected_model['display']} for this chat! 💕✨",
            parse_mode='Markdown'
        )
        
        logger.info(f"Model changed to {selected_model['display']} for chat {chat_id} by admin {user_id}")
    
    async def character_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /character command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return
        
        # Show current settings if no arguments
        if not context.args:
            current_char = db.get_character_for_chat(chat_id)
            
            character_info = f"""
🎭 **Current Character Settings for Leyana:**

👤 **Name:** {current_char['name']}
💫 **Personality:** {current_char['personality']}
✨ **Traits:** {current_char['traits']}
💬 **Style:** {current_char['style']}
🎯 **Behavior:** {current_char['behavior']}

**📝 How to customize:**
`/character name <new_name>`
`/character personality <description>`
`/character traits <trait_list>`
`/character style <communication_style>`
`/character behavior <behavior_description>`
`/character reset` - Reset to default

**💡 Examples:**
`/character name Luna`
`/character personality cute anime girl who loves gaming`
`/character traits shy, kawaii, loves memes, supportive`
`/character style uses lots of anime emojis and uwu speech`
`/character behavior acts like a tsundere, loves roleplay`
            """
            
            await update.message.reply_text(character_info, parse_mode='Markdown')
            return
        
        # Parse command arguments
        if len(context.args) < 2:
            await update.message.reply_text("❌ Please specify what to change and the new value.\nUse `/character` to see examples.")
            return

        setting = context.args[0].lower()
        new_value = ' '.join(context.args[1:])
        
        # Handle reset command
        if setting == 'reset':
            db.reset_character(chat_id)
            await update.message.reply_text("✅ **Character reset to default!**\n\n🎭 Leyana is back to her original personality! 💕")
            return
        
        # Update the specified setting
        if setting == 'name':
            db.set_character_setting(chat_id, 'name', new_value)
            await update.message.reply_text(f"✅ **Name updated!**\n\n👤 I'm now **{new_value}**! Nice to meet you! 😊💕")
            
        elif setting == 'personality':
            db.set_character_setting(chat_id, 'personality', new_value)
            await update.message.reply_text(f"✅ **Personality updated!**\n\n💫 My new personality: *{new_value}*\n\nI feel different already! ✨")
            
        elif setting == 'traits':
            db.set_character_setting(chat_id, 'traits', new_value)
            await update.message.reply_text(f"✅ **Traits updated!**\n\n✨ My new traits: *{new_value}*\n\nThese describe me perfectly! 💕")
            
        elif setting == 'style':
            db.set_character_setting(chat_id, 'style', new_value)
            await update.message.reply_text(f"✅ **Communication style updated!**\n\n💬 My new style: *{new_value}*\n\nI'll chat this way from now on! 🎯")
            
        elif setting == 'behavior':
            db.set_character_setting(chat_id, 'behavior', new_value)
            await update.message.reply_text(f"✅ **Behavior updated!**\n\n🎯 My new behavior: *{new_value}*\n\nThis is how I'll act! 🎭")
            
        else:
            await update.message.reply_text("❌ Invalid setting! Use: name, personality, traits, style, behavior, or reset")
            return
        
        logger.info(f"Character {setting} updated for chat {chat_id} by admin {user_id}: {new_value}")

    async def addapi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addapi command to add new API keys"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        # Validate input
        if not context.args:
            await update.message.reply_text("""
❌ Please provide an API key and optional name.

**Usage:** 
`/addapi YOUR_API_KEY [Name]`

**Examples:**
`/addapi AIza...xyz Main_API`
`/addapi AIza...abc Backup_API`

⚠️ The message will be deleted after processing for security.
            """, parse_mode='Markdown')
            return

        api_key = context.args[0]
        api_name = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        # Add API key
        success, message = api_manager.add_api_key(api_key, api_name)
        
        # Delete command message for security
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except:
            pass
        
        await update.effective_chat.send_message(message)
        
        if success:
            logger.info(f"API key added by admin {user_id}")

    async def removeapi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removeapi command to remove API keys"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        if not context.args:
            await update.message.reply_text("❌ Please provide API ID to remove.\nUse `/listapis` to see available APIs.")
            return

        api_id = context.args[0]
        success, message = api_manager.remove_api_key(api_id)
        
        await update.message.reply_text(message)
        
        if success:
            logger.info(f"API key {api_id} removed by admin {user_id}")

    async def listapis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listapis command to list all API keys"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        api_details = api_manager.get_api_details()
        
        if not api_details:
            await update.message.reply_text("❌ No API keys configured. Use `/addapi` to add API keys.")
            return

        message = "🔑 **API Keys Management:**\n\n"
        
        for api in api_details:
            status_emoji = {
                'active': '✅',
                'failed': '❌', 
                'cooldown': '⏳',
                'disabled': '🚫'
            }.get(api['status'], '❓')
            
            message += f"**{api['name']}** {status_emoji}\n"
            message += f"└ ID: `{api['id']}`\n"
            message += f"└ Key: `{api['masked_key']}`\n"
            message += f"└ Status: {api['status'].title()}\n"
            message += f"└ Requests: {api['total_requests']} (Success: {api['success_rate']:.1f}%)\n"
            
            if api['last_error'] and api['status'] != 'active':
                message += f"└ Last Error: {api['last_error'][:50]}...\n"
            
            message += "\n"

        message += f"**Commands:**\n"
        message += f"`/removeapi <id>` - Remove API key\n"
        message += f"`/toggleapi <id>` - Enable/disable API key\n"
        message += f"`/apistat` - Detailed statistics"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def apistat_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /apistat command to show API statistics"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        stats = api_manager.get_api_statistics()
        
        message = f"""
📊 **API Statistics Dashboard:**

**📈 Overall Performance:**
• Total APIs: {stats['total_apis']}
• Active APIs: {stats['active_apis']} ✅
• Failed APIs: {stats['failed_apis']} ❌
• Disabled APIs: {stats['disabled_apis']} 🚫
• Cooldown APIs: {stats['cooldown_apis']} ⏳

**📊 Request Statistics:**
• Total Requests: {stats['total_requests']:,}
• Successful Requests: {stats['total_successes']:,}
• Overall Success Rate: {stats['success_rate']:.2f}%

**🔄 Load Balancing:**
• Failover System: {'🟢 Active' if stats['active_apis'] > 1 else '🟡 Limited' if stats['active_apis'] == 1 else '🔴 Offline'}
• Redundancy: {'🟢 High' if stats['active_apis'] >= 3 else '🟡 Medium' if stats['active_apis'] == 2 else '🔴 Low'}

**💡 Recommendations:**
        """
        
        if stats['active_apis'] == 0:
            message += "• ⚠️ **CRITICAL**: No active APIs! Add API keys immediately.\n"
        elif stats['active_apis'] == 1:
            message += "• ⚠️ **WARNING**: Only 1 active API. Add more for redundancy.\n"
        elif stats['active_apis'] < 3:
            message += "• 💡 **SUGGESTION**: Add more API keys for better load distribution.\n"
        else:
            message += "• ✅ **EXCELLENT**: Good API redundancy and load balancing.\n"
        
        if stats['success_rate'] < 90 and stats['total_requests'] > 10:
            message += "• 🔧 **ATTENTION**: Low success rate. Check API key validity.\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def toggleapi_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /toggleapi command to enable/disable API keys"""
        user_id = update.effective_user.id
        
        if not db.is_admin(user_id):
            if db.get_admin_id() == 0:
                await update.message.reply_text("❌ No admin set. Use /setadmin first to become admin.")
            else:
                await update.message.reply_text("❌ This command is only available to the bot admin.")
            return

        if not context.args:
            await update.message.reply_text("❌ Please provide API ID to toggle.\nUse `/listapis` to see available APIs.")
            return

        api_id = context.args[0]
        
        # Get current status and toggle
        api_details = api_manager.get_api_details()
        current_api = next((api for api in api_details if api['id'] == api_id), None)
        
        if not current_api:
            await update.message.reply_text("❌ API key not found.")
            return

        if current_api['status'] == 'disabled':
            success, message = api_manager.enable_api_key(api_id)
        else:
            success, message = api_manager.disable_api_key(api_id)
        
        await update.message.reply_text(message)
        
        if success:
            action = "enabled" if current_api['status'] == 'disabled' else "disabled"
            logger.info(f"API key {api_id} {action} by admin {user_id}")

# Global command handlers instance
command_handlers = CommandHandlers()