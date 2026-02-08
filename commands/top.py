"""
Handlers for stats commands (admins only).

Full stats and top-10 players.
"""
import aiosqlite
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from loguru import logger

from config import CHAT_ID
from data.levels import LEVELS
from data.texts import (
    ADMIN_ONLY,
    EMPTY_DB,
    LEVEL_FALLBACK,
    NO_PLAYERS_IN_RATING,
    STATS_HEADER,
    STATS_LINE,
    TOP10_HEADER,
    TOP10_LINE,
    TOP_DM_FAIL,
    TOP_SENT_DM,
)
from database import get_db
from utils import format_user_mention, is_admin

router = Router()


@router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    """
    Admin command: send full stats to DMs.

    Fetches all players from DB and sends stats to the requesting admin.

    Args:
        message: Incoming message

    Raises:
        Exception: On DB or send errors
    """
    if message.from_user is None or message.bot is None:
        return
    if not is_admin(str(message.from_user.id)):
        name_mention = format_user_mention(
            message.from_user.id, message.from_user.first_name or ""
        )
        await message.answer(ADMIN_ONLY.format(name=name_mention))
        return

    async with get_db() as db_conn:
        db: aiosqlite.Connection = db_conn
        cur = await db.execute("""
            SELECT first_name, level, total_orders, has_student_done, has_critic_done,
                   has_dirty_plate_done, has_second_chef_done
            FROM users
            ORDER BY total_orders DESC, level DESC
        """)
        rows = await cur.fetchall()

    admin_id = str(message.from_user.id)

    if not rows:
        try:
            await message.bot.send_message(chat_id=admin_id, text=EMPTY_DB)
            if message.chat.type != "private":
                await message.answer(TOP_SENT_DM)
        except Exception:
            if message.chat.type != "private" and message.from_user is not None:
                name_mention = format_user_mention(
                    message.from_user.id, message.from_user.first_name or ""
                )
                await message.answer(TOP_DM_FAIL.format(name=name_mention))
        return

    lines = [STATS_HEADER]
    for i, r in enumerate(rows, start=1):
        level_title = LEVELS.get(r["level"], LEVEL_FALLBACK.format(level=r["level"]))
        student = "✅" if r["has_student_done"] else "❌"
        critic = "✅" if r["has_critic_done"] else "❌"
        dirty = "✅" if r["has_dirty_plate_done"] else "❌"
        chef = "✅" if r["has_second_chef_done"] else "❌"
        lines.append(STATS_LINE.format(
            num=i,
            name=r["first_name"] or "",
            orders=r["total_orders"],
            level=level_title,
            student=student,
            critic=critic,
            dirty=dirty,
            chef=chef
        ))
    text = "\n".join(lines)

    try:
        await message.bot.send_message(chat_id=admin_id, text=text)
        if message.chat.type != "private":
            await message.answer(TOP_SENT_DM)
    except Exception:
        if message.chat.type != "private" and message.from_user is not None:
            name_mention = format_user_mention(
                message.from_user.id, message.from_user.first_name or ""
            )
            await message.answer(TOP_DM_FAIL.format(name=name_mention))


@router.message(Command("top10"))
async def cmd_top10(message: Message) -> None:
    """
    Admin command: show top-10 players in chat.

    Fetches top-10 by completed orders and posts ranking. Game chat only.

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

        if CHAT_ID and str(message.chat.id) != str(CHAT_ID):
            return

        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            cur = await db.execute(
                """
                SELECT user_id, first_name, level, total_orders
                FROM users
                ORDER BY total_orders DESC, level DESC
                LIMIT 10
            """
            )
            rows = await cur.fetchall()

        if not rows:
            await message.answer(NO_PLAYERS_IN_RATING)
            return

        lines = [TOP10_HEADER]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

        for i, r in enumerate(rows):
            level_title = LEVELS.get(r["level"], LEVEL_FALLBACK.format(level=r["level"]))
            medal = medals[i] if i < len(medals) else f"{i+1}."
            name_mention = format_user_mention(r["user_id"], r["first_name"] or "")
            lines.append(
                TOP10_LINE.format(
                    medal=medal, name=name_mention, orders=r["total_orders"], level=level_title
                )
            )

        text = "\n".join(lines)
        await message.answer(text)
    except Exception as e:
        user_id = message.from_user.id if message.from_user is not None else "?"
        logger.error(f"Error fetching top-10 for user {user_id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при получении рейтинга. Попробуйте позже.",
            )
        except Exception:
            pass
