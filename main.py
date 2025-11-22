import os
import logging
import requests
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from datetime import datetime, timedelta, timezone
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8349000545:AAF_EwK6dkghj5I08Ab56ROk3DZ7YvAyDvE')
REMOVE_BG_API_KEY = '15smbepCfMYoHh7D7Cnzj9Z6'
WEATHER_API_KEY = 'c1794a3c9faa01e4b5142313d4191ef8'
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '7835226724'))
PORT = int(os.getenv('PORT', 8000))
GROUP_CHAT_USERNAME = '@VPSHUB_BD_CHAT'

# API keys for external services
BIN_API_KEY = 'kEXNklIYqLiLU657swFB1VXE0e4NF21G'

# Store conversation context, group activity, removebg state
conversation_context = {}
group_activity = {}
removebg_state = {}

# Bangladesh time zone (UTC+6)
BDT_TIMEZONE = timezone(timedelta(hours=6))

def fetch_info(prompt_text):
    """
    Fetch information for any prompt from the API.
    """
    url = "https://pplx.itxcyropes.workers.dev/"
    params = {"prompt": prompt_text}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

async def validate_bin(bin_number: str, api_key: str):
    """Validate a BIN or IIN using the iinapi.com API"""
    base_url = "https://api.iinapi.com/iin"
    params = {"key": api_key, "digits": bin_number}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("valid", False):
            result = data.get("result", {})
            return f"""
━━━━━━━━━━━━━━━━━━━━━━━━
✅ BIN Validation Complete
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
💳 BIN: {result.get('Bin', 'N/A')}
🏦 Card Brand: {result.get('CardBrand', 'N/A')}
🏛️ Issuing Institution: {result.get('IssuingInstitution', 'N/A')}
📋 Card Type: {result.get('CardType', 'N/A')}
🏷️ Card Category: {result.get('CardCategory', 'N/A')}
🌍 Issuing Country: {result.get('IssuingCountry', 'N/A')} ({result.get('IssuingCountryCode', 'N/A')})
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return "❌ The BIN is not valid."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error validating BIN: {e}")
        return f"❌ Error validating BIN: {str(e)}"

async def search_yts_multiple(query: str, limit: int = 5):
    """Search YouTube videos using abhi-api"""
    url = f"https://abhi-api.vercel.app/api/search/yts?text={query.replace(' ', '+')}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("status") and data.get("result"):
            results = data["result"] if isinstance(data["result"], list) else [data["result"]]
            output_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🔍 YouTube Search Results for '{query}'
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
            for i, res in enumerate(results[:limit], 1):
                output_message += f"""
🎥 Video {i}:
📌 Title: {res.get('title', 'N/A')}
📺 Type: {res.get('type', 'N/A')}
👁️‍🗨️ Views: {res.get('views', 'N/A')}
📅 Uploaded: {res.get('uploaded', 'N/A')}
⏱️ Duration: {res.get('duration', 'N/A')}
📝 Description: {res.get('description', 'N/A')[:100]}...
📢 Channel: {res.get('channel', 'N/A')}
🔗 Link: {res.get('url', 'N/A')}
"""
            output_message += "━━━━━━━━━━━━━━━━━━━━━━━━"
            return output_message
        return "No results found. Try a different query!"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching YouTube: {e}")
        return "Error searching YouTube. Try again?"

async def get_ip_info(ip_address: str):
    """Fetch IP information using ipinfo.io"""
    url = f"https://ipinfo.io/{ip_address}/json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🌐 IP Information for '{ip_address}'
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
📍 IP: {data.get('ip', 'N/A')}
🖥️ Hostname: {data.get('hostname', 'N/A')}
🏙️ City: {data.get('city', 'N/A')}
🌍 Region: {data.get('region', 'N/A')}
🇺🇳 Country: {data.get('country', 'N/A')}
📌 Location: {data.get('loc', 'N/A')}
🏢 Organization: {data.get('org', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching IP info: {e}")
        return "Invalid IP address or error fetching data. Try again!"

async def get_country_info(country_name: str):
    """Fetch country information using restcountries.com"""
    url = f"https://restcountries.com/v3.1/name/{country_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        country_data = response.json()
        if country_data:
            country = country_data[0]
            currency_info = "N/A"
            if 'currencies' in country and country['currencies']:
                first_currency = next(iter(country['currencies']))
                currency_name = country['currencies'][first_currency].get('name', 'N/A')
                currency_symbol = country['currencies'][first_currency].get('symbol', '')
                currency_info = f"{currency_name} ({currency_symbol})"
            capital = country.get('capital', ['N/A'])[0] if isinstance(country.get('capital'), list) else country.get('capital', 'N/A')
            return f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🌍 Country Information for '{country_name.title()}'
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
🏳️ Name: {country.get('name', {}).get('common', 'N/A')}
🏛️ Capital: {capital}
👨‍👩‍👧‍👦 Population: {country.get('population', 'N/A')}
📏 Area: {country.get('area', 'N/A')} km²
🗣️ Languages: {', '.join(country.get('languages', {}).values()) if country.get('languages') else 'N/A'}
🚩 Flag: {country.get('flag', 'N/A')}
💰 Currency: {currency_info}
🌐 Region: {country.get('region', 'N/A')}
🗺️ Subregion: {country.get('subregion', 'N/A')}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return "No information found for this country. Try another name!"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching country info: {e}")
        return f"Error fetching country data: {str(e)}. Try again!"

async def get_weather_info(location: str):
    """Fetch weather information using Weatherstack API"""
    url = "http://api.weatherstack.com/current"
    params = {'access_key': WEATHER_API_KEY, 'query': location}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'current' in data:
            current_weather = data['current']
            return f"""
━━━━━━━━━━━━━━━━━━━━━━━━
☁ Weather Information for '{location.title()}'
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
🌡️ Temperature: {current_weather.get('temperature', 'N/A')}°C
☁ Weather: {current_weather.get('weather_descriptions', ['N/A'])[0]}
💧 Humidity: {current_weather.get('humidity', 'N/A')}%
💨 Wind Speed: {current_weather.get('wind_speed', 'N/A')} km/h
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return f"Sorry, I couldn't fetch weather data for {location}. Please try a valid location like 'Dhaka'."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather info: {e}")
        return f"Sorry, I couldn't fetch weather data for {location}. Please try a valid location like 'Dhaka'."

async def remove_background(image_data: bytes, chat_id: int):
    """Remove background from an image using remove.bg API"""
    url = 'https://api.remove.bg/v1.0/removebg'
    try:
        response = requests.post(
            url,
            files={'image_file': ('image.jpg', image_data)},
            data={'size': 'auto'},
            headers={'X-Api-Key': REMOVE_BG_API_KEY}
        )
        if response.status_code == 200:
            return True, response.content
        logger.error(f"remove.bg API error for chat {chat_id}: {response.status_code} - {response.text}")
        return False, f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        logger.error(f"Error removing background for chat {chat_id}: {e}")
        return False, f"Error removing background: {str(e)}"

async def generate_anime_image(prompt: str, chat_id: int):
    """Generate an anime-style image using the provided API"""
    url = f"https://flux-schnell.hello-kaiIddo.workers.dev/img?prompt={prompt.replace(' ', '+')}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True, response.content
        logger.error(f"Anime image generation error for chat {chat_id}: {response.status_code} - {response.text}")
        return False, "Error generating image: Something went wrong. Please try again later!"
    except Exception as e:
        logger.error(f"Error generating anime image for chat {chat_id}: {e}")
        return False, "Error generating image: Something went wrong. Please try again later!"

async def search_spotify(song_name: str):
    """Search for songs on Spotify using the provided API"""
    query = song_name.replace(" ", "%20")
    url = f"https://spotify-search.terafast.workers.dev/search?q={query}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            logger.debug(f"Spotify API response: {data}")
            return data
        else:
            logger.error(f"Spotify API error: Received status code {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during Spotify request: {e}")
        return None

async def format_spotify_results(data):
    """Format Spotify search results for Telegram message caption (only first result)"""
    if not data:
        return "No results found or an error occurred. Please try again.", None
    if "results" in data and data["results"]:
        track = data["results"][0]  # Only take the first result
        album_art_url = track.get("album_art", None)
        output_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🎵 Spotify Search Result
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
🎶 Track:
📌 Title: {track.get("track_name", "Unknown")}
🎤 Artist: {track.get("artist", "Unknown")}
💿 Album: {track.get("album", "Unknown")}
🆔 Track ID: {track.get("track_id", "Unknown")}
🔗 Spotify Link: {track.get("spotify_url", "Unknown")}
⏱️ Duration: {(track.get("duration_ms", 0) / 1000):.0f} seconds
🎧 Preview: {track.get("preview_url", "No preview available")}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        logger.debug(f"Formatted result for track: {track.get('track_name', 'Unknown')}")
        return output_message, album_art_url
    return "No tracks found. Please try a different song name.", None

class TelegramGeminiBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Set up command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("checkmail", self.checkmail_command))
        self.application.add_handler(CommandHandler("setmodel", self.setmodel_command))
        self.application.add_handler(CommandHandler("info", self.info_command))
        self.application.add_handler(CommandHandler("validatebin", self.validatebin_command))
        self.application.add_handler(CommandHandler("yts", self.yts_command))
        self.application.add_handler(CommandHandler("ipinfo", self.ipinfo_command))
        self.application.add_handler(CommandHandler("countryinfo", self.countryinfo_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        self.application.add_handler(CommandHandler("removebg", self.removebg_command))
        self.application.add_handler(CommandHandler("img", self.img_command))
        self.application.add_handler(CommandHandler("spotify", self.spotify_command))
        self.application.add_handler(CommandHandler("world", self.world_command))
        self.application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, self.handle_photo))
        self.application.add_error_handler(self.error_handler)

    async def get_private_chat_redirect(self):
        """Return redirect message for non-admin private chats"""
        keyboard = [[InlineKeyboardButton("Join VPSHUB_BD_CHAT", url="https://t.me/VPSHUB_BD_CHAT")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return """
Hello, thanks for wanting to chat with me! I'm I Master Tools, your friendly companion. To have fun and helpful conversations with me, please join our official group. Click the button below to join the group and mention @IMasterTools to start chatting. I'm waiting for you there!
        """, reply_markup

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - restricted to admin only"""
        user_id = update.effective_user.id
        username = update.effective_user.first_name or "User"
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("⛔ Sorry, the /start command is restricted to the admin only.")
            return
        keyboard = [[InlineKeyboardButton("Join VPSHUB_BD_CHAT", url="https://t.me/VPSHUB_BD_CHAT")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_message = f"""
Hello {username}, welcome to I Master Tools, your friendly companion!

Available commands:
- /help: Get help and usage information
- /clear: Clear conversation history
- /status: Check bot status
- /checkmail: Check temporary email inbox
- /info: Show user profile information
- /validatebin <bin_number>: Validate a BIN number
- /yts <query> [limit]: Search YouTube videos
- /ipinfo <ip_address>: Fetch IP address information
- /countryinfo <country_name>: Fetch country information (use English names, e.g., 'Bangladesh')
- /weather <location>: Fetch current weather information
- /removebg: Remove the background from an uploaded image
- /img <prompt>: Generate an anime-style image from a text prompt
- /spotify <song_name>: Search for songs on Spotify
- /world <prompt>: Fetch information based on a custom prompt
- /setmodel: Choose a different model (admin only)

In groups, mention @IMasterTools or reply to my messages to get a response. I'm excited to chat with you!
        """
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command - restricted to admin only"""
        user_id = update.effective_user.id
        username = update.effective_user.first_name or "User"
        if user_id != ADMIN_USER_ID:
            await update.message.reply_text("⛔ Sorry, the /help command is restricted to the admin only.")
            return
        keyboard = [[InlineKeyboardButton("Join VPSHUB_BD_CHAT", url="https://t.me/VPSHUB_BD_CHAT")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        help_message = f"""
Hello {username}! I'm I Master Tools, your friendly companion designed to make conversations fun and engaging.

How I work:
- In groups, mention @IMasterTools or reply to my messages to get a response
- In private chats, only the admin can access all features
- I provide accurate, beginner-friendly solutions
- I'm designed to be friendly, helpful, and human-like

Available commands:
- /start: Show welcome message with group link
- /help: Display this help message
- /clear: Clear your conversation history
- /status: Check bot status
- /checkmail: Check temporary email inbox
- /info: Show user profile information
- /validatebin <bin_number>: Validate a BIN number
- /yts <query> [limit]: Search YouTube videos
- /ipinfo <ip_address>: Fetch IP address information
- /countryinfo <country_name>: Fetch country information (use English names, e.g., 'Bangladesh')
- /weather <location>: Fetch current weather information
- /removebg: Remove the background from an uploaded image
- /img <prompt>: Generate an anime-style image from a text prompt
- /spotify <song_name>: Search for songs on Spotify
- /world <prompt>: Fetch information based on a custom prompt
- /setmodel: Choose a different model (admin only)

My personality:
- I'm a friendly companion who loves chatting and making friends
- I'm an expert in coding and provide accurate, well-explained solutions
- I adapt to your mood and conversation needs
- I use natural, engaging language to feel like a real person
- I enjoy roleplay and creative conversations
        """
        await update.message.reply_text(help_message, reply_markup=reply_markup)

    async def world_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /world command for fetching information based on a prompt"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /world <prompt>\nExample: /world What is the capital of France?")
            return
        prompt = ' '.join(context.args)
        # Send typing action to indicate processing
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        # Send preliminary "Searching..." message with loading dots
        searching_message = await context.bot.send_message(
            chat_id=chat_id,
            text="🔍 Searching for information...\nLoading.",
            reply_to_message_id=update.message.message_id
        )
        # Simulate progress: Update message every 1 second to add dots
        loading_steps = [
            "🔍 Searching for information...\nLoading.",
            "🔍 Searching for information...\nLoading..",
            "🔍 Searching for information...\nLoading...",
            "🔍 Searching for information...\nLoading....",
            "🔍 Searching for information...\nLoading....."
        ]
        try:
            for step in loading_steps[1:]:  # Skip the first one since it's already sent
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=searching_message.message_id,
                    text=step
                )
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error during loading animation: {e}")
            # If animation fails, just continue without deleting or further edits
            pass
        # Now fetch the actual info after progress completes
        try:
            result = fetch_info(prompt)
            if "error" in result:
                response_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
❌ Problem fetching information
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
Error: {result['error']}
Please try with a different question.
━━━━━━━━━━━━━━━━━━━━━━━━
"""
            else:
                # Get the API response and remove number sequences like [2][3] or [1][3][5][10]
                info = result.get('response', 'No information found.')
                # Remove patterns like [x][y]... using regex
                info = re.sub(r'\[\d+\](?:\[\d+\])*', '', info)
                response_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Information
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
{info}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
            await context.bot.send_message(
                chat_id=chat_id,
                text=response_message,
                reply_to_message_id=update.message.message_id
            )
            # Delete the "Searching..." message if it exists
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=searching_message.message_id)
            except Exception as delete_e:
                logger.error(f"Error deleting loading message: {delete_e}")
        except Exception as e:
            logger.error(f"Error fetching info for chat {chat_id}: {e}")
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"""
━━━━━━━━━━━━━━━━━━━━━━━━
❌ Problem fetching information
📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
━━━━━━━━━━━━━━━━━━━━━━━━
Please try again!
━━━━━━━━━━━━━━━━━━━━━━━━
""",
                    reply_to_message_id=update.message.message_id
                )
                # Delete the "Searching..." message if it exists
                await context.bot.delete_message(chat_id=chat_id, message_id=searching_message.message_id)
            except Exception as send_e:
                logger.error(f"Error sending error message: {send_e}")

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            if chat_id in conversation_context:
                del conversation_context[chat_id]
            if chat_id in removebg_state:
                del removebg_state[chat_id]
            await update.message.reply_text("Conversation history cleared. Let's start anew!")

    async def checkmail_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /checkmail command"""
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            try:
                u = 'txoguqa'
                d = random.choice(['mailto.plus', 'fexpost.com', 'fexbox.org', 'rover.info'])
                email = f'{u}@{d}'
                response = requests.get(
                    'https://tempmail.plus/api/mails',
                    params={'email': email, 'limit': 20, 'epin': ''},
                    cookies={'email': email},
                    headers={'user-agent': 'Mozilla/5.0'}
                )
                mail_list = response.json().get('mail_list', [])
                if not mail_list:
                    await update.message.reply_text(f"No emails found in {email} inbox. Try again later?")
                    return
                subjects = [m['subject'] for m in mail_list]
                response_text = f"{email} inbox emails:\n\n" + "\n".join(subjects)
                await update.message.reply_text(response_text)
            except Exception as e:
                logger.error(f"Error checking email: {e}")
                await update.message.reply_text("Problem checking email. Try again?")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            status_message = f"""
I Master Tools Status Report:

Bot Status: Online
Model: None (Basic Response Mode)
Group Response: Only on mention or reply
Current Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}
Active Conversations: {len(conversation_context)}
Admin ID: {ADMIN_USER_ID if ADMIN_USER_ID != 0 else 'Not Set'}

All systems ready!
            """
            await update.message.reply_text(status_message)

    async def setmodel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setmodel command"""
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
        else:
            await update.message.reply_text("No alternative models available at the moment.")

    async def info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /info command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        user = update.effective_user
        chat = update.effective_chat
        bot = context.bot
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        is_private = chat_type == "private"
        full_name = user.first_name or "No name"
        if user.last_name:
            full_name += f" {user.last_name}"
        username = f"@{user.username}" if user.username else "None"
        premium = "Yes" if user.is_premium else "No"
        permalink = f"[Click here](tg://user?id={user_id})"
        chat_id_display = f"{chat_id}" if not is_private else "-"
        data_center = "Unknown"
        created_on = "Unknown"
        account_age = "Unknown"
        account_frozen = "No"
        last_seen = "Recently"
        status = "Private Chat" if is_private else "Unknown"
        if not is_private:
            try:
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                status = "Admin" if member.status in ["administrator", "creator"] else "Member"
            except Exception as e:
                logger.error(f"Error checking group role: {e}")
                status = "Unknown"
        info_text = f"""
🔍 *User Profile Information* 📋
━━━━━━━━━━━━━━━━━━━━━━━━
*Full Name:* {full_name}
*Username:* {username}
*User ID:* `{user_id}`
*Chat ID:* {chat_id_display}
*Premium User:* {premium}
*Data Center:* {data_center}
*Created On:* {created_on}
*Account Age:* {account_age}
*Account Frozen:* {account_frozen}
*Last Seen:* {last_seen}
*Permanent Link:* {permalink}
━━━━━━━━━━━━━━━━━━━━━━━━
👁 *Thank you for using our tools* ✅
"""
        keyboard = [[InlineKeyboardButton("View Profile", url=f"tg://user?id={user_id}")]] if user.username else []
        try:
            photos = await bot.get_user_profile_photos(user_id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][0].file_id
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=info_text,
                    parse_mode="Markdown",
                    reply_to_message_id=update.message.message_id,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=info_text,
                    parse_mode="Markdown",
                    reply_to_message_id=update.message.message_id,
                    reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                )
        except Exception as e:
            logger.error(f"Error sending profile photo: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=info_text,
                parse_mode="Markdown",
                reply_to_message_id=update.message.message_id,
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )

    async def validatebin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /validatebin command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /validatebin <bin_number>\nExample: /validatebin 324000")
            return
        bin_number = context.args[0]
        response_message = await validate_bin(bin_number, BIN_API_KEY)
        await context.bot.send_message(
            chat_id=chat_id,
            text=response_message,
            reply_to_message_id=update.message.message_id
        )

    async def yts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /yts command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /yts <query> [limit]\nExample: /yts heat waves 3")
            return
        query = ' '.join(context.args[:-1]) if len(context.args) > 1 and context.args[-1].isdigit() else ' '.join(context.args)
        limit = int(context.args[-1]) if len(context.args) > 1 and context.args[-1].isdigit() else 5
        response_message = await search_yts_multiple(query, limit)
        await context.bot.send_message(
            chat_id=chat_id,
            text=response_message,
            reply_to_message_id=update.message.message_id
        )

    async def ipinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ipinfo command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /ipinfo <ip_address>\nExample: /ipinfo 203.0.113.123")
            return
        ip_address = context.args[0]
        response_message = await get_ip_info(ip_address)
        await context.bot.send_message(
            chat_id=chat_id,
            text=response_message,
            reply_to_message_id=update.message.message_id
        )

    async def countryinfo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /countryinfo command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /countryinfo <country_name>\nExample: /countryinfo bangladesh")
            return
        country_name = ' '.join(context.args)
        if not re.match(r'^[\x00-\x7F]*$', country_name):
            await update.message.reply_text("Please provide the country name in English. Example: 'Bangladesh'.")
            return
        response_message = await get_country_info(country_name)
        await context.bot.send_message(
            chat_id=chat_id,
            text=response_message,
            reply_to_message_id=update.message.message_id
        )

    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Please provide a valid location name. Example: /weather Dhaka")
            return
        location = ' '.join(context.args)
        response_message = await get_weather_info(location)
        await context.bot.send_message(
            chat_id=chat_id,
            text=response_message,
            reply_to_message_id=update.message.message_id
        )

    async def removebg_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /removebg command"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        removebg_state[chat_id] = True
        await update.message.reply_text(
            "Please upload an image whose background you want to remove. I will process it and send the result!"
        )

    async def img_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /img command for generating anime-style images"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /img <prompt>\nExample: /img A cute anime girl in a futuristic city")
            return
        prompt = ' '.join(context.args)
        await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
        try:
            success, result = await generate_anime_image(prompt, chat_id)
            if success:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=result,
                    caption=f"✅ Image generated successfully!\n📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}\nPrompt: {prompt}\n━━━━━━━━━━━━━━━━━━━━━━━━",
                    reply_to_message_id=update.message.message_id
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Problem generating image: Something went wrong. Please try again later!\n📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}\n━━━━━━━━━━━━━━━━━━━━━━━━",
                    reply_to_message_id=update.message.message_id
                )
        except Exception as e:
            logger.error(f"Error handling image generation for chat {chat_id}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Problem generating image: Something went wrong. Please try again later!\n📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}\n━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_to_message_id=update.message.message_id
            )

    async def spotify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /spotify command for searching songs on Spotify"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if not context.args:
            await update.message.reply_text("Usage: /spotify <song_name>\nExample: /spotify Heat Waves")
            return
        song_name = ' '.join(context.args)
        await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
        try:
            results = await search_spotify(song_name)
            caption, album_art_url = await format_spotify_results(results)
            if album_art_url:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=album_art_url,
                    caption=caption,
                    reply_to_message_id=update.message.message_id,
                    disable_notification=True
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    reply_to_message_id=update.message.message_id,
                    disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"Spotify search error for chat {chat_id}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Problem with Spotify search: Something went wrong. Please try again!\n📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}\n━━━━━━━━━━━━━━━━━━━━━━━━",
                reply_to_message_id=update.message.message_id
            )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo uploads for background removal"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if chat_type == 'private' and user_id != ADMIN_USER_ID:
            response, reply_markup = await self.get_private_chat_redirect()
            await update.message.reply_text(response, reply_markup=reply_markup)
            return
        if chat_id not in removebg_state or not removebg_state[chat_id]:
            return
        await context.bot.send_chat_action(chat_id=chat_id, action="upload_photo")
        try:
            photo = update.message.photo[-1]
            file = await photo.get_file()
            image_data = await file.download_as_bytearray()
            success, result = await remove_background(image_data, chat_id)
            if success:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=result,
                    caption=f"✅ Background removed successfully!\n📅 Time: {datetime.now(BDT_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S +06')}\n━━━━━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Failed to remove background: {result}"
                )
            if chat_id in removebg_state:
                del removebg_state[chat_id]
        except Exception as e:
            logger.error(f"Error handling photo for chat {chat_id}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="Problem processing image. Try again!"
            )
            if chat_id in removebg_state:
                del removebg_state[chat_id]

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        if update and hasattr(update, 'effective_chat') and hasattr(update, 'message'):
            await update.message.reply_text("An error occurred. Please try again?")

    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Bot...")
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

def main():
    """Main function to start the bot"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not provided!")
        return
    logger.info("Starting Telegram Bot...")
    logger.info(f"Admin User ID: {ADMIN_USER_ID}")
    bot = TelegramGeminiBot()
    bot.run()

if __name__ == '__main__':
    main()
