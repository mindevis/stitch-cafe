"""
Handlers for /start and chat member join events.

Greets users and automatically welcomes new chat members.
"""
from typing import cast

import aiosqlite
from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.types import ChatMemberUpdated, Message, ReplyKeyboardRemove
from loguru import logger

from config import CHAT_ID
from data.texts import HELLO, SELECT_ACTION
from database import _UserLike, ensure_user, get_db
from keyboards.main_menu import main_menu_kb
from utils import format_user_mention

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle /start command.

    Registers user in database and sends welcome message with inline buttons.
    Works in both private chat and groups.

    Args:
        message: Incoming message

    Raises:
        Exception: On DB or send errors
    """
    if message.from_user is None:
        return
    try:
        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            await ensure_user(db, cast(_UserLike, message.from_user))

        keyboard = main_menu_kb()
        name_mention = format_user_mention(
            message.from_user.id, message.from_user.first_name or ""
        )
        await message.answer(
            HELLO.format(name=name_mention),
            reply_markup=ReplyKeyboardRemove(),
        )
        await message.answer(SELECT_ACTION, reply_markup=keyboard)
    except Exception as e:
        user_id = message.from_user.id if message.from_user is not None else "?"
        logger.error(f"Error handling /start for user {user_id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при запуске. Попробуйте позже.",
            )
        except Exception:
            pass


@router.chat_member()
async def on_new_member(event: ChatMemberUpdated) -> None:
    """
    Handle new chat member join.

    Welcomes new members in the game chat, registers them and sends welcome message.

    Args:
        event: Chat member update event

    Raises:
        Exception: On DB or send errors
    """
    try:
        if not CHAT_ID or str(event.chat.id) != str(CHAT_ID):
            return

        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        if old_status != ChatMemberStatus.MEMBER and new_status == ChatMemberStatus.MEMBER:
            new_member = event.new_chat_member.user

            if new_member.is_bot:
                return
            if event.bot is None:
                return

            async with get_db() as db_conn:
                db: aiosqlite.Connection = db_conn
                await ensure_user(db, cast(_UserLike, new_member))

            keyboard = main_menu_kb()
            name_mention = format_user_mention(new_member.id, new_member.first_name or "")
            await event.bot.send_message(
                chat_id=event.chat.id,
                text=HELLO.format(name=name_mention),
                reply_markup=ReplyKeyboardRemove(),
            )
            await event.bot.send_message(
                chat_id=event.chat.id, text=SELECT_ACTION, reply_markup=keyboard
            )
    except Exception as e:
        new_user = event.new_chat_member.user
        user_id = new_user.id if new_user is not None else "?"
        logger.error(f"Error welcoming new member {user_id}: {e}")
