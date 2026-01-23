"""
Модуль обработки заказов.

Содержит обработчики для создания, просмотра и завершения заказов.
Поддерживает как текстовые команды, так и inline-кнопки.
"""
import random
from typing import Union

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
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
    finish_order_and_level,
    get_active_order,
    get_db,
    get_last_order,
    save_active_order,
    fetch_user,
)
from keyboards.main_menu import CALLBACK_DONE, CALLBACK_MY, CALLBACK_NEW, main_menu_kb
from utils import format_user_mention

router = Router()


async def generate_regular_order(level: int) -> list[tuple[str, int]]:
    """
    Генерирует обычный заказ из 3 блюд.
    
    Алгоритм:
    - 1 блюдо с текущего уровня
    - 2 блюда из всех открытых уровней (0..level)
    - Без повторов
    
    Args:
        level: Текущий уровень игрока
        
    Returns:
        Список из 3 кортежей (название блюда, количество крестиков)
    """
    opened = []
    for lv in range(0, level+1):
        opened.extend(DISHES_BY_LEVEL.get(lv, []))
    current_pool = DISHES_BY_LEVEL.get(level, DISHES_BY_LEVEL[0])
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
    Вычисляет номер нового заказа.
    
    Args:
        total_orders: Количество уже завершенных заказов
        
    Returns:
        Номер нового заказа (завершенные + 1)
    """
    return (total_orders or 0) + 1


async def _handle_new_order(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик для создания нового заказа.
    
    Работает как с текстовыми командами, так и с inline-кнопками.
    Генерирует обычный или специальный заказ в зависимости от условий.
    
    Args:
        message_or_query: Объект Message или CallbackQuery
        
    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # Определяем тип объекта и получаем нужные атрибуты
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            from_user = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()  # Убираем индикатор загрузки
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        # Игровые команды только в указанной группе
        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT, parse_mode="HTML")
            return

        async with get_db() as db:
            user = await fetch_user(db, from_user.id, from_user.first_name)
            active = await get_active_order(db, user["user_id"])

            if active is not None:
                name_mention = format_user_mention(from_user.id, user["first_name"])
                await message.answer(
                    ALREADY_HAS_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
                return

            idx = _order_index(user["total_orders"])

            # Проверяем, был ли предыдущий заказ специальным
            last_order_was_special = False
            if user["total_orders"] > 0:
                last_order = await get_last_order(db, user["user_id"])
                if last_order and last_order.get("tag"):
                    last_order_was_special = True

            # Проверка специальных заказов-событий
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
                    # Грязная тарелка - удвоить предыдущий заказ
                    last_order = await get_last_order(db, user["user_id"])
                    if last_order:
                        last_dishes = last_order.get("dishes", [])
                        last_crosses = last_order.get("crosses", 0)
                        doubled_dishes = [(name, crosses * 2) for name, crosses in last_dishes]
                        doubled_crosses = last_crosses * 2
                        name_mention = format_user_mention(from_user.id, user["first_name"])
                        text = order_config["text_template"].format(
                            name=name_mention, doubled_crosses=doubled_crosses
                        )
                        await save_active_order(db, user["user_id"], doubled_dishes, tag)
                        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
                        return
                    # Если нет предыдущего заказа, генерируем обычный
                elif order_type == "half_next":
                    # Второй повар - следующий заказ будет половинным
                    await db.execute(
                        "UPDATE users SET has_second_chef_done=1, next_order_half=1 WHERE user_id=?",
                        (user["user_id"],),
                    )
                    await db.commit()
                    name_mention = format_user_mention(from_user.id, user["first_name"])
                    text = order_config["text_template"].format(name=name_mention)
                    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
                    return
                elif order_type == "regular":
                    # Обычный специальный заказ (студент, критик)
                    dishes = [order_config["dish"]]
                    name_mention = format_user_mention(from_user.id, user["first_name"])
                    text = order_config["text_template"].format(name=name_mention)
                    await save_active_order(db, user["user_id"], dishes, tag)
                    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
                    return

            # Обычный заказ
            level = user["level"]
            dishes = await generate_regular_order(level)

            # Проверяем флаг "следующий заказ половинный"
            next_order_half = user.get("next_order_half", 0)
            if next_order_half:
                # Делаем заказ половинным и сбрасываем флаг
                dishes = [(name, max(1, crosses // 2)) for name, crosses in dishes]
                await db.execute(
                    "UPDATE users SET next_order_half=0 WHERE user_id=?", (user["user_id"],)
                )
                await db.commit()

            total = sum(x[1] for x in dishes)
            lines = "\n".join([DISH_LINE.format(name=n, crosses=v) for (n, v) in dishes])
            name_mention = format_user_mention(from_user.id, user["first_name"])
            order_number = _order_index(user["total_orders"])
            text = (
                NEW_ORDER_MESSAGE.format(
                    name=name_mention, order_number=order_number, dishes=lines
                )
                + ORDER_TOTAL.format(total=total)
            )
            await save_active_order(db, user["user_id"], dishes, None)
            await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка создания заказа для пользователя {from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при создании заказа. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass  # Если не удалось отправить сообщение об ошибке


@router.message(Command("new"))
@router.message(Command("neworder"))
@router.callback_query(F.data == CALLBACK_NEW)
async def new_order(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик команды /new или нажатия кнопки "Новый заказ".
    
    Args:
        message_or_query: Объект Message или CallbackQuery
    """
    await _handle_new_order(message_or_query)

async def _handle_my_order(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик для просмотра текущего активного заказа.
    
    Работает как с текстовыми командами, так и с inline-кнопками.
    
    Args:
        message_or_query: Объект Message или CallbackQuery
        
    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # Определяем тип объекта и получаем нужные атрибуты
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            from_user = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()  # Убираем индикатор загрузки
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT, parse_mode="HTML")
            return

        async with get_db() as db:
            user = await fetch_user(db, from_user.id, from_user.first_name)
            active = await get_active_order(db, user["user_id"])
            if not active:
                name_mention = format_user_mention(from_user.id, user["first_name"])
                await message.answer(
                    NO_ACTIVE_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
                return
            dishes = active["dishes"]
            lines = "\n".join([DISH_LINE.format(name=n, crosses=v) for (n, v) in dishes])
            total = sum(v for (_, v) in dishes)
            name_mention = format_user_mention(from_user.id, user["first_name"])
            text = (
                f"{SHOW_ORDER_HEADER.format(name=name_mention)}\n\n{lines}"
                + ORDER_TOTAL.format(total=total)
            )
            await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка просмотра заказа для пользователя {from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при просмотре заказа. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(Command("my"))
@router.message(Command("myorder"))
@router.callback_query(F.data == CALLBACK_MY)
async def my_order(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик команды /my или нажатия кнопки "Мой заказ".
    
    Args:
        message_or_query: Объект Message или CallbackQuery
    """
    await _handle_my_order(message_or_query)

async def _handle_done(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик для завершения заказа.
    
    Работает как с текстовыми командами, так и с inline-кнопками.
    Обновляет статистику, проверяет повышение уровня и достижения.
    
    Args:
        message_or_query: Объект Message или CallbackQuery
        
    Raises:
        Exception: При ошибках работы с БД или отправки сообщений
    """
    try:
        # Определяем тип объекта и получаем нужные атрибуты
        if isinstance(message_or_query, CallbackQuery):
            message = message_or_query.message
            from_user = message_or_query.from_user
            chat = message.chat
            await message_or_query.answer()  # Убираем индикатор загрузки
        else:
            message = message_or_query
            from_user = message.from_user
            chat = message.chat

        if CHAT_ID and str(chat.id) != str(CHAT_ID):
            await message.answer(WRONG_CHAT, parse_mode="HTML")
            return

        async with get_db() as db:
            user = await fetch_user(db, from_user.id, from_user.first_name)
            active = await get_active_order(db, user["user_id"])
            if not active:
                name_mention = format_user_mention(from_user.id, user["first_name"])
                await message.answer(
                    NO_ACTIVE_ORDER.format(name=name_mention),
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
                return

            # Подсчитываем крестики в текущем заказе
            order_crosses = sum(v for (_, v) in active["dishes"])

            # Завершаем заказ и обновляем статистику
            n_total, level_changed, new_title, total_crosses = await finish_order_and_level(
                db, user["user_id"], active["tag"], order_crosses
            )
            await clear_active_order(db, user["user_id"])

            # Формируем сообщение в зависимости от событий
            name_mention = format_user_mention(from_user.id, user["first_name"])
            if level_changed:
                # Новый уровень
                txt = DONE_WITH_LEVEL_UP.format(name=name_mention, n=n_total, title=new_title)
            else:
                # Базовое сообщение
                txt = DONE_ORDER.format(name=name_mention, n=n_total)

            # Проверяем достижения (40, 100 и 200 заказов)
            if n_total == 40:
                txt += GAME_COMPLETE
            elif n_total == 100:
                txt += TROPHY_GOLD
            elif n_total == 200:
                txt += TROPHY_DIAMOND

            await message.answer(txt, reply_markup=main_menu_kb(), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Ошибка завершения заказа для пользователя {from_user.id}: {e}")
        try:
            await message.answer(
                "❌ Произошла ошибка при завершении заказа. Попробуйте позже.",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.message(Command("done"))
@router.callback_query(F.data == CALLBACK_DONE)
async def done(message_or_query: Union[Message, CallbackQuery]) -> None:
    """
    Обработчик команды /done или нажатия кнопки "Готово".
    
    Args:
        message_or_query: Объект Message или CallbackQuery
    """
    await _handle_done(message_or_query)
