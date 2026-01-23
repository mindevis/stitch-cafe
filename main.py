"""
Точка входа для Telegram-бота "Вышивальное кафе".

Модуль инициализирует бота, настраивает логирование и запускает обработку обновлений.
"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from loguru import logger
from config import BOT_TOKEN
from commands.start import router as start_router
from commands.order import router as order_router
from commands.reset import router as reset_router
from commands.top import router as top_router

# Настройка логирования через loguru
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    encoding="utf-8"
)


async def main() -> None:
    """
    Главная функция запуска бота.
    
    Инициализирует бота, регистрирует роутеры и запускает polling.
    Обрабатывает ошибки запуска и логирует их.
    
    Raises:
        RuntimeError: Если BOT_TOKEN не задан в переменных окружения.
    """
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан. Заполните .env")
        raise RuntimeError("BOT_TOKEN не задан. Заполните .env")
    
    try:
        logger.info("Запуск бота...")
        # Для aiogram 3.3.0 используем простой способ создания бота
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        dp = Dispatcher()
        dp.include_router(start_router)
        dp.include_router(order_router)
        dp.include_router(reset_router)
        dp.include_router(top_router)

        logger.info("Бот запущен и готов к работе")
        # Включаем получение событий о новых участниках
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member"])
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка при работе бота: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
