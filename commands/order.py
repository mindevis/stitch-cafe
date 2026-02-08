"""
Order handlers.

Create, view and complete orders. Supports text commands and inline buttons.
"""
import random

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, User
from loguru import logger

from config import CHAT_ID
from data.dishes import DISHES_BY_LEVEL
from data.special_orders import check_special_order
from data.texts import (
    ALREADY_HAS_ORDER,
    DISH_LINE,
    DONE_ORDER,
    DONE_WITH_LEVEL_UP,
    GAME_COMPLETE,
    NEW_ORDER_MESSAGE,
    NO_ACTIVE_ORDER,
    ORDER_TOTAL,
    SHOW_ORDER_HEADER,
    TROPHY_DIAMOND,
    TROPHY_GOLD,
    WRONG_CHAT,
)
from database import (
    clear_active_order,
    fetch_user,
    finish_order_and_level,
    get_active_order,
    get_db,
    get_last_order,
    save_active_order,
)
from keyboards.main_menu import CALLBACK_DONE, CALLBACK_MY, CALLBACK_NEW, main_menu_kb
from utils import format_user_mention

router = Router()


async def generate_regular_order(level: int) -> list[tuple[str, int]]:
    """
    Generate a regular order of 3 dishes.

    One dish from current level, two from all unlocked levels (0..level), no duplicates.

    Args:
        level: Player's current level

    Returns:
        List of 3 (dish_name, crosses) tuples
    """
    dish_level = min(level, 3)
    opened = []
    for lv in range(0, dish_level + 1):
        opened.extend(DISHES_BY_LEVEL.get(lv, []))
    current_pool = DISHES_BY_LEVEL.get(dish_level, DISHES_BY_LEVEL[0])
    cur = random.choice(current_pool)
    pool = [d for d in opened if d != cur]
    random.shuffle(pool)
    take = [cur]
    for d in pool:
        if d not in take and len(take) < 3:
            take.append(d)
    while len(take) < 3:
        for d in DISHES_BY_LEVEL[0]:
            if d not in take:
                take.append(d)
            if len(take) == 3:
                break
    return take[:3]

def _order_index(total_orders: int) -> int:
    """
    Compute the next order number.

    Args:
        total_orders: Number of completed orders so far

    Returns:
        Next order number (completed + 1)
    """
    return (total_orders or 0) + 1


async def _handle_new_order(
    message_or_query: Message | CallbackQuery,
) -> None:
    """
    Handler for creating a new order.

    Works with text commands and inline buttons. Generates regular or special order.

    Args:
        message_or_query: Message or CallbackQuery

    Raises:
        Exception: On DB or send errors
    """
    try:
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            if message is None:
                await message_or_query.answer()
                return
            from_user: User | None = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        if from_user is None or not isinstance(message, Message):
            return
        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT)
            return

        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            user = await fetch_user(db, from_user.id, from_user.first_name or "")
            active = await get_active_order(db, user["user_id"])

            if active is not None:
                name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
                await message.answer(
                    ALREADY_HAS_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                )
                return

            idx = _order_index(user["total_orders"])

            last_order_was_special = False
            if user["total_orders"] > 0:
                last_order = await get_last_order(db, user["user_id"])
                if last_order and last_order.get("tag"):
                    last_order_was_special = True

            if not last_order_was_special:
                user_flags = {
                    "has_student_done": user.get("has_student_done", 0),
                    "has_critic_done": user.get("has_critic_done", 0),
                    "has_dirty_plate_done": user.get("has_dirty_plate_done", 0),
                    "has_second_chef_done": user.get("has_second_chef_done", 0),
                }
                special_result = check_special_order(idx, user_flags)
            else:
                special_result = None

            if special_result:
                tag, order_config = special_result
                order_type = order_config.get("type", "regular")

                if order_type == "double_previous":
                    last_order = await get_last_order(db, user["user_id"])
                    if last_order:
                        last_dishes = last_order.get("dishes", [])
                        last_crosses = last_order.get("crosses", 0)
                        doubled_dishes = [
                            (name, crosses * 2) for name, crosses in last_dishes
                        ]
                        doubled_crosses = last_crosses * 2
                        name_mention = format_user_mention(
                            from_user.id, user.get("first_name") or ""
                        )
                        text = order_config["text_template"].format(
                            name=name_mention, doubled_crosses=doubled_crosses
                        )
                        await save_active_order(db, user["user_id"], doubled_dishes, tag)
                        await message.answer(text, reply_markup=main_menu_kb())
                        return
                elif order_type == "half_new_order":
                    level = user["level"]
                    dishes = await generate_regular_order(level)
                    total = sum(c for (_, c) in dishes)
                    half_total = total // 2
                    half_dishes = [(name, max(1, crosses // 2)) for name, crosses in dishes]
                    half_crosses = sum(v for (_, v) in half_dishes)
                    if half_dishes and half_crosses != half_total:
                        diff = half_total - half_crosses
                        name0, val0 = half_dishes[0]
                        half_dishes[0] = (name0, max(1, val0 + diff))
                        half_crosses = half_total
                    lines = "\n".join(
                        [DISH_LINE.format(name=n, crosses=v) for (n, v) in half_dishes]
                    )
                    name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
                    text = order_config["text_template"].format(
                        name=name_mention, half_crosses=half_crosses, dishes=lines
                    )
                    await save_active_order(db, user["user_id"], half_dishes, tag)
                    await message.answer(text, reply_markup=main_menu_kb())
                    return
                elif order_type == "regular":
                    dishes = [order_config["dish"]]
                    name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
                    text = order_config["text_template"].format(name=name_mention)
                    await save_active_order(db, user["user_id"], dishes, tag)
                    await message.answer(text, reply_markup=main_menu_kb())
                    return

            level = user["level"]
            dishes = await generate_regular_order(level)
            total = sum(x[1] for x in dishes)
            lines = "\n".join([DISH_LINE.format(name=n, crosses=v) for (n, v) in dishes])
            name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
            order_number = _order_index(user["total_orders"])
            text = (
                NEW_ORDER_MESSAGE.format(
                    name=name_mention, order_number=order_number, dishes=lines
                )
                + ORDER_TOTAL.format(total=total)
            )
            await save_active_order(db, user["user_id"], dishes, None)
            await message.answer(text, reply_markup=main_menu_kb())
    except Exception as e:
        logger.error(
            f"Error creating order for user {from_user.id if from_user is not None else '?'}: {e}"
        )
        try:
            if isinstance(message, Message):
                await message.answer(
                    "❌ Произошла ошибка при создании заказа. Попробуйте позже.",
                )
        except Exception:
            pass


@router.message(Command("new"))
@router.message(Command("neworder"))
@router.callback_query(F.data == CALLBACK_NEW)
async def new_order(message_or_query: Message | CallbackQuery) -> None:
    """
    Handle /new command or "New order" button.

    Args:
        message_or_query: Message or CallbackQuery
    """
    await _handle_new_order(message_or_query)


async def _handle_my_order(
    message_or_query: Message | CallbackQuery,
) -> None:
    """
    Handler for viewing current active order.

    Works with text commands and inline buttons.

    Args:
        message_or_query: Message or CallbackQuery

    Raises:
        Exception: On DB or send errors
    """
    try:
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            if message is None:
                await message_or_query.answer()
                return
            from_user: User | None = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        if from_user is None or not isinstance(message, Message):
            return
        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT)
            return

        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            user = await fetch_user(db, from_user.id, from_user.first_name or "")
            active = await get_active_order(db, user["user_id"])
            if not active:
                name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
                await message.answer(
                    NO_ACTIVE_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                )
                return
            dishes = active["dishes"]
            lines = "\n".join([DISH_LINE.format(name=n, crosses=v) for (n, v) in dishes])
            total = sum(v for (_, v) in dishes)
            name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
            text = (
                f"{SHOW_ORDER_HEADER.format(name=name_mention)}\n\n{lines}"
                + ORDER_TOTAL.format(total=total)
            )
            await message.answer(text, reply_markup=main_menu_kb())
    except Exception as e:
        logger.error(
            f"Error viewing order for user {from_user.id if from_user is not None else '?'}: {e}"
        )
        try:
            if isinstance(message, Message):
                await message.answer(
                    "❌ Произошла ошибка при просмотре заказа. Попробуйте позже.",
                )
        except Exception:
            pass


@router.message(Command("my"))
@router.message(Command("myorder"))
@router.callback_query(F.data == CALLBACK_MY)
async def my_order(message_or_query: Message | CallbackQuery) -> None:
    """
    Handle /my command or "My order" button.

    Args:
        message_or_query: Message or CallbackQuery
    """
    await _handle_my_order(message_or_query)


async def _handle_done(
    message_or_query: Message | CallbackQuery,
) -> None:
    """
    Handler for completing an order.

    Works with text commands and inline buttons. Updates stats, level and achievements.

    Args:
        message_or_query: Message or CallbackQuery

    Raises:
        Exception: On DB or send errors
    """
    try:
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            if message is None:
                await message_or_query.answer()
                return
            from_user: User | None = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        if from_user is None or not isinstance(message, Message):
            return
        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT)
            return

        async with get_db() as db_conn:
            db: aiosqlite.Connection = db_conn
            user = await fetch_user(db, from_user.id, from_user.first_name or "")
            active = await get_active_order(db, user["user_id"])
            if not active:
                name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
                await message.answer(
                    NO_ACTIVE_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                )
                return

            order_crosses = sum(v for (_, v) in active["dishes"])
            n_total, level_changed, new_title, total_crosses = await finish_order_and_level(
                db, user["user_id"], active["tag"], order_crosses
            )
            await clear_active_order(db, user["user_id"])

            name_mention = format_user_mention(from_user.id, user.get("first_name") or "")
            if level_changed:
                txt = DONE_WITH_LEVEL_UP.format(
                    name=name_mention,
                    n=n_total,
                    title=new_title,
                    total_crosses=total_crosses,
                )
            else:
                txt = DONE_ORDER.format(
                    name=name_mention,
                    n=n_total,
                    total_crosses=total_crosses,
                    title=new_title,
                )

            if n_total == 40:
                txt += GAME_COMPLETE
            elif n_total == 100:
                txt += TROPHY_GOLD
            elif n_total == 200:
                txt += TROPHY_DIAMOND

            await message.answer(txt, reply_markup=main_menu_kb())
    except Exception as e:
        logger.error(
            f"Error completing order for user {from_user.id if from_user is not None else '?'}: {e}"
        )
        try:
            if isinstance(message, Message):
                await message.answer(
                    "❌ Произошла ошибка при завершении заказа. Попробуйте позже.",
                )
        except Exception:
            pass


@router.message(Command("done"))
@router.callback_query(F.data == CALLBACK_DONE)
async def done(message_or_query: Message | CallbackQuery) -> None:
    """
    Handle /done command or "Done" button.

    Args:
        message_or_query: Message or CallbackQuery
    """
    await _handle_done(message_or_query)
