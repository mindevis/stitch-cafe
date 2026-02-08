"""
Main menu keyboard.

Inline keyboard with main player actions.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_NEW = "order_new"
CALLBACK_MY = "order_my"
CALLBACK_DONE = "order_done"


def main_menu_kb() -> InlineKeyboardMarkup:
    """
    Build main menu with inline buttons (New order, My order, Done).

    Returns:
        InlineKeyboardMarkup
    """
    kb = [
        [InlineKeyboardButton(text="🧾 Новый заказ", callback_data=CALLBACK_NEW)],
        [
            InlineKeyboardButton(text="📋 Мой заказ", callback_data=CALLBACK_MY),
            InlineKeyboardButton(text="✅ Готово", callback_data=CALLBACK_DONE),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
