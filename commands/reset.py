"""
Модуль обработки команды /reset (только для администраторов).

Позволяет администраторам полностью очистить базу данных пользователей.
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
    Обработчик команды /reset.
    
    Полностью очищает базу данных пользователей. Доступна только
    администраторам. Работает везде (в личке и в чате).
    
    Args:
        message: Объект сообщения от пользователя
        
    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # Только админ, работает везде (в личке и в чате)
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
        logger.warning(f"Администратор {message.from_user.id} очистил базу данных")
        await message.answer(RESET_SUCCESS.format(name=name_mention), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка сброса данных администратором {message.from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при сбросе данных. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass
