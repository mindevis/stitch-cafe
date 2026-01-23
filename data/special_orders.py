"""
Модуль специальных заказов-событий.

Определяет специальные события игры (студент, критик, грязная тарелка, второй повар)
с их вероятностями, условиями и текстами сообщений.
"""
import random
from typing import Optional

from data.texts import (
    CRITIC_APPEAR,
    DIRTY_PLATE_APPEAR,
    SECOND_CHEF_APPEAR,
    STUDENT_APPEAR,
)

# Определение специальных заказов-событий
SPECIAL_ORDERS = {
    "dirty_plate": {
        "text_template": DIRTY_PLATE_APPEAR,
        "probability": 0.15,  # 15%
        "min_order_index": 3,
        "max_order_index": 40,
        "user_flag": "has_dirty_plate_done",
        "type": "double_previous",  # Удвоить предыдущий заказ
    },
    "student": {
        "dish": ("🥡 Лапша быстрого приготовления", 100),
        "text_template": STUDENT_APPEAR,
        "probability": 0.12,  # 12%
        "min_order_index": 3,
        "max_order_index": 40,
        "user_flag": "has_student_done",
        "type": "regular",  # Обычный специальный заказ
    },
    "critic": {
        "dish": ("🦪 Устрицы", 1000),
        "text_template": CRITIC_APPEAR,
        "probability": 0.10,  # 10%
        "min_order_index": 20,
        "max_order_index": 40,
        "user_flag": "has_critic_done",
        "type": "regular",  # Обычный специальный заказ
    },
    "second_chef": {
        "text_template": SECOND_CHEF_APPEAR,
        "probability": 0.12,  # 12%
        "min_order_index": 3,
        "max_order_index": 40,
        "user_flag": "has_second_chef_done",
        "type": "half_next",  # Следующий заказ будет половинным
    },
}

def check_special_order(
    order_index: int, user_flags: dict
) -> Optional[tuple[str, dict]]:
    """
    Проверяет, должен ли выпасть специальный заказ.

    Проверяет каждое специальное событие по порядку:
    1. Условия по номеру заказа (min_order_index, max_order_index)
    2. Флаг выполнения события (не должно быть выполнено ранее)
    3. Вероятность выпадения

    Args:
        order_index: Номер текущего заказа (1-based)
        user_flags: Словарь с флагами пользователя:
            - has_student_done: Выполнен ли заказ студента
            - has_critic_done: Выполнен ли заказ критика
            - has_dirty_plate_done: Выполнено ли событие грязной тарелки
            - has_second_chef_done: Выполнено ли событие второго повара

    Returns:
        Кортеж (tag, order_config) если выпал спецзаказ, иначе None.
        tag может быть: "student", "critic", "dirty_plate", "second_chef"
    """
    # Проверяем каждое событие в порядке приоритета
    for tag, order_config in SPECIAL_ORDERS.items():
        # Проверка условия по номеру заказа
        if order_config["min_order_index"] and order_index < order_config["min_order_index"]:
            continue
        if order_config["max_order_index"] and order_index > order_config["max_order_index"]:
            continue
        
        # Проверка, выполнено ли уже это событие
        flag_name = order_config["user_flag"]
        if user_flags.get(flag_name, 0):
            continue
        
        # Проверка вероятности
        if random.random() < order_config["probability"]:
            return tag, order_config
    
    return None
