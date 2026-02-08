"""
Handler for /reset command (admins only).

Allows admins to wipe the user database.
"""
import aiosqlite
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
    if message.from_user is None:
        return
    try:
        if not is_admin(str(message.from_user.id)):
            name_mention = format_user_mention(
                message.from_user.id, message.from_user.first_name or ""
            )
            await message.answer(ADMIN_ONLY.format(name=name_mention))
            return

        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            await db.execute("DELETE FROM users")
            await db.commit()
        name_mention = format_user_mention(
            message.from_user.id, message.from_user.first_name or ""
        )
        logger.warning(f"Admin {message.from_user.id} cleared the database")
        await message.answer(RESET_SUCCESS.format(name=name_mention))
    except Exception as e:
        admin_id = message.from_user.id if message.from_user is not None else "?"
        logger.error(f"Error resetting data by admin {admin_id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при сбросе данных. Попробуйте позже.",
            )
        except Exception:
            pass
