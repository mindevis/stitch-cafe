"""
Модуль конфигурации бота.

Загружает переменные окружения из .env файла и предоставляет
настройки для работы бота.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID игрового чата, где работает бот
CHAT_ID = os.getenv("CHAT_ID", "")

# Строка с ID админов через запятую (например: "123,456")
ADMIN_IDS_STR = os.getenv("ADMIN_ID", "")

# Список ID админов (парсится из ADMIN_IDS_STR)
ADMIN_IDS = [aid.strip() for aid in ADMIN_IDS_STR.split(",") if aid.strip()] if ADMIN_IDS_STR else []
