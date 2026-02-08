"""
Bot configuration module.

Loads environment variables from .env and provides bot settings.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Bot token from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Game chat ID where the bot operates
CHAT_ID = os.getenv("CHAT_ID", "")

# Comma-separated admin IDs (e.g. "123,456")
ADMIN_IDS_STR = os.getenv("ADMIN_ID", "")

# List of admin IDs (parsed from ADMIN_IDS_STR)
ADMIN_IDS = (
    [aid.strip() for aid in ADMIN_IDS_STR.split(",") if aid.strip()]
    if ADMIN_IDS_STR
    else []
)
