"""
Handler for /reset command (admins only).

Allows admins to wipe the user database.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from data.texts import ADMIN_ONLY, RESET_SUCCESS
from database import get_db
from utils import format_user_mention, is_admin

router = Router()


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """
    Handle /reset command.

    Clears the user database. Admins only. Works in private chat and groups.

    Args:
        message: Incoming message

    Raises:
        Exception: On DB or send errors
    """
    try:
        if not is_admin(str(message.from_user.id)):
            name_mention = format_user_mention(
                message.from_user.id, message.from_user.first_name
            )
            await message.answer(ADMIN_ONLY.format(name=name_mention), parse_mode="HTML")
            return

        async with get_db() as db:
            await db.execute("DELETE FROM users")
            await db.commit()
        name_mention = format_user_mention(message.from_user.id, message.from_user.first_name)
        logger.warning(f"Admin {message.from_user.id} cleared the database")
        await message.answer(RESET_SUCCESS.format(name=name_mention), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error resetting data by admin {message.from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при сбросе данных. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass
