"""
Модуль главного меню бота.

Содержит inline-клавиатуру с основными действиями игрока.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Константы для callback_data кнопок
CALLBACK_NEW = "order_new"
CALLBACK_MY = "order_my"
CALLBACK_DONE = "order_done"


def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Создает главное меню с inline-кнопками.

    Returns:
        InlineKeyboardMarkup с кнопками:
        - 🧾 Новый заказ
        - 📋 Мой заказ | ✅ Готово
    """
    kb = [
        [InlineKeyboardButton(text="🧾 Новый заказ", callback_data=CALLBACK_NEW)],
        [
            InlineKeyboardButton(text="📋 Мой заказ", callback_data=CALLBACK_MY),
            InlineKeyboardButton(text="✅ Готово", callback_data=CALLBACK_DONE),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
