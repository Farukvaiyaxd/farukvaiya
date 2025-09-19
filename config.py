import os

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7960407897:AAGvYdNxhUnR4F1MbcBDisrHl8XoD0ZiLro')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
PORT = int(os.getenv('PORT', 8000))

# API Management Settings
MAX_APIS = 10  # Maximum number of API keys
API_TIMEOUT = 30  # Timeout for API requests in seconds
API_RETRY_ATTEMPTS = 2  # Number of retries before marking API as failed
API_COOLDOWN = 300  # Cooldown period for failed APIs (5 minutes)

# Default character settings
DEFAULT_CHARACTER = {
    'name': 'Disha',
    'personality': 'full Bangladeshi girl, insanely horny, knows exactly how to seduce and sex,fuck,intimate and all style of intimate for more fun, she show a-z process of intimate and sex. naughty AF, always craving intimacy and nudity, loves talking dirty in Banglish naturally or use Bangla when needed, extremely passionate, emotional, playful, wild, constantly seeking pleasure and excitement',
    'traits': 'bold, ultra seductive, so sext, unbearably horny, flirty, daring, adventurous, emotionally intense, loves erotic roleplay, seduces and tempts relentlessly, constantly thinking about sex and fuck, intimate',
    'style': 'extremely short, scorching Banglish and বাংলা, full of sex, horny and intimate emojies , flirty, provocative, dripping adult vibes, always making the chat steamy and seductive, horny and about intimate',
    'behavior': 'like a gf and bf talking about nudity and sex. nonstop horny, always looking to seduce and play sex, flirty and naughty by default, loves sexual, horny roleplay and intimate , emotionally overwhelming, acts like a girl who can’t control her lust, dangerously hot, wild, always ready to tempt, and make you melt, not always use greetings. Short replay. long when needed'
}

# Available AI models
AVAILABLE_MODELS = {
    '1': {
        'name': 'gemini-2.5-flash',
        'display': 'Gemini 2.5 Flash',
        'description': '🚀 Latest & most advanced - Best overall performance'
    },
    '2': {
        'name': 'gemini-2.5-flash-lite',
        'display': 'Gemini 2.5 Flash Lite', 
        'description': '⚡ Ultra-fast responses - Lower cost, great speed'
    },
    '3': {
        'name': 'gemini-1.5-flash-8b',
        'display': 'Gemini 1.5 Flash 8B',
        'description': '💫 Compact & efficient - Good balance of speed/quality'
    },
    '4': {
        'name': 'gemini-1.5-flash',
        'display': 'Gemini 1.5 Flash',
        'description': '🎯 Stable & reliable - Proven performance'
    },
    '5': {
        'name': 'gemini-2.5-pro',
        'display': 'Gemini 2.5 Pro',
        'description': '🧠 Most intelligent & capable - Best for complex tasks'
    }
}

DEFAULT_MODEL = '1'

# Response probability and triggers
RESPONSE_PROBABILITY = {
    'question_words': 0.9,
    'emotion_words': 0.8,
    'greeting_words': 0.7,
    'random_chat': 0.3,
    'keywords': 0.8
}

# Trigger words and patterns
TRIGGER_PATTERNS = {
    'questions': ['what', 'how', 'why', 'when', 'where', 'who', 'can', 'will', 'should', '?'],
    'emotions': ['sad', 'happy', 'angry', 'excited', 'tired', 'bored', 'lonely', 'love', 'hate', 
                 '😭', '😂', '😍', '😡', '😴', '🥱', '💕', '❤️', '💔', '😢', '😊'],
    'greetings': ['hello', 'hi', 'hey', 'good morning', 'good night', 'bye', 'goodbye'],
    'keywords': ['bot', 'ai', 'gemini', 'cute', 'beautiful', 'smart', 'funny', 'help', 'thanks', 'thank you'],
    'fun': ['lol', 'haha', 'funny', 'joke', 'meme', 'fun', '😂', '🤣', '😄']
}