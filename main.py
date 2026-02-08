"""
Entry point for the Telegram bot "Stitch Cafe".

Initializes the bot, configures logging and starts update polling.
"""
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from commands.order import router as order_router
from commands.reset import router as reset_router
from commands.start import router as start_router
from commands.top import router as top_router
from config import BOT_TOKEN

# Logging setup via loguru
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
    Main entry point for starting the bot.

    Initializes the bot, registers routers and starts polling.
    Handles startup errors and logs them.

    Raises:
        RuntimeError: If BOT_TOKEN is not set in environment variables.
    """
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Fill in .env")
        raise RuntimeError("BOT_TOKEN is not set. Fill in .env")

    try:
        logger.info("Starting bot...")
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(start_router)
        dp.include_router(order_router)
        dp.include_router(reset_router)
        dp.include_router(top_router)

        logger.info("Bot is up and ready")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member"])
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Critical error while running bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
