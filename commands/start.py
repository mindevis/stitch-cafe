"""
Модуль обработки команды /start и событий добавления участников.

Содержит обработчики для приветствия пользователей и автоматического
приветствия новых участников чата.
"""
from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import ChatMemberUpdated, Message, ReplyKeyboardRemove
from loguru import logger

from config import CHAT_ID
from data.texts import HELLO, SELECT_ACTION
from database import ensure_user, get_db
from keyboards.main_menu import main_menu_kb
from utils import format_user_mention

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Обработчик команды /start.

    Регистрирует пользователя в базе данных и отправляет приветственное
    сообщение с inline-кнопками. Работает везде (в личке и в чате).

    Args:
        message: Объект сообщения от пользователя

    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # /start работает везде (в личке и в чате)
        async with get_db() as db:
            await ensure_user(db, message.from_user)

        # Убираем старую ReplyKeyboard (если она была) и отправляем inline кнопки
        keyboard = main_menu_kb()
        name_mention = format_user_mention(message.from_user.id, message.from_user.first_name)
        await message.answer(
            HELLO.format(name=name_mention),
            reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
            parse_mode="HTML",
        )
        # Отправляем inline кнопки отдельным сообщением
        await message.answer(SELECT_ACTION, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка обработки /start для пользователя {message.from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при запуске. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.chat_member()
async def on_new_member(event: ChatMemberUpdated) -> None:
    """
    Обработчик добавления нового участника в чат.

    Автоматически приветствует новых участников в игровом чате,
    регистрирует их в базе данных и отправляет приветственное сообщение.

    Args:
        event: Событие обновления статуса участника чата

    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # Проверяем, что это нужный чат
        if not CHAT_ID or str(event.chat.id) != str(CHAT_ID):
            return

        # Проверяем, что пользователь стал участником
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        # Если пользователь стал участником
        if old_status != ChatMemberStatus.MEMBER and new_status == ChatMemberStatus.MEMBER:
            # Получаем пользователя, который присоединился
            new_member = event.new_chat_member.user

            # Пропускаем ботов
            if new_member.is_bot:
                return

            # Регистрируем пользователя в базе данных
            async with get_db() as db:
                await ensure_user(db, new_member)

            # Отправляем приветственное сообщение с кнопками
            keyboard = main_menu_kb()
            name_mention = format_user_mention(new_member.id, new_member.first_name)
            await event.bot.send_message(
                chat_id=event.chat.id,
                text=HELLO.format(name=name_mention),
                reply_markup=ReplyKeyboardRemove(remove_keyboard=True),
                parse_mode="HTML",
            )
            await event.bot.send_message(
                chat_id=event.chat.id, text=SELECT_ACTION, reply_markup=keyboard, parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"Ошибка приветствия нового участника {event.new_chat_member.user.id}: {e}")
