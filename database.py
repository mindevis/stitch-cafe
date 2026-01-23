"""
Модуль для работы с базой данных SQLite.

Предоставляет функции для работы с пользователями, заказами
и статистикой игры.
"""
import json
from contextlib import asynccontextmanager
from typing import Optional

import aiosqlite
from loguru import logger

from data.levels import LEVELS, MAX_LEVEL, ORDERS_PER_LEVEL

DB_PATH = "data/cafe.db"


@asynccontextmanager
async def get_db():
    """
    Контекстный менеджер для работы с базой данных.
    
    Автоматически создает подключение, выполняет миграции
    и закрывает подключение при выходе из контекста.
    
    Yields:
        aiosqlite.Connection: Подключение к базе данных
        
    Raises:
        aiosqlite.Error: При ошибках подключения к БД
    """
    db = None
    try:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        await migrate(db)
        yield db
    except aiosqlite.Error as e:
        logger.error(f"Ошибка работы с БД: {e}")
        raise
    finally:
        if db:
            await db.close()

async def migrate(db: aiosqlite.Connection) -> None:
    """
    Выполняет миграции базы данных.
    
    Создает таблицу users если её нет, и добавляет новые поля
    при необходимости.
    
    Args:
        db: Подключение к базе данных
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запросов
    """
    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                level INTEGER DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                total_crosses INTEGER DEFAULT 0,
                has_student_done INTEGER DEFAULT 0,
                has_dirty_plate_done INTEGER DEFAULT 0,
                has_critic_done INTEGER DEFAULT 0,
                has_second_chef_done INTEGER DEFAULT 0,
                next_order_half INTEGER DEFAULT 0,
                last_order_json TEXT,
                active_order_json TEXT
            );
            """
        )
        # Миграция: добавляем новые поля если их нет
        migrations = [
            "ALTER TABLE users ADD COLUMN total_crosses INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN has_dirty_plate_done INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN has_critic_done INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN has_second_chef_done INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN next_order_half INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_order_json TEXT",
        ]
        for migration in migrations:
            try:
                await db.execute(migration)
            except aiosqlite.OperationalError:
                # Поле уже существует - это нормально
                pass
        await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"Ошибка миграции БД: {e}")
        raise

async def ensure_user(db: aiosqlite.Connection, from_user) -> None:
    """
    Создает пользователя в базе данных, если его еще нет.
    
    Args:
        db: Подключение к базе данных
        from_user: Объект пользователя Telegram (с атрибутами id и first_name)
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
    """
    try:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, first_name) VALUES (?, ?)",
            (from_user.id, from_user.first_name or "Гость"),
        )
        await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"Ошибка создания пользователя {from_user.id}: {e}")
        raise


async def fetch_user(db: aiosqlite.Connection, user_id: int, first_name: str) -> dict:
    """
    Получает данные пользователя из базы данных.
    
    Если пользователя нет, создает его автоматически.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        first_name: Имя пользователя
        
    Returns:
        Словарь с данными пользователя
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
    """
    try:
        await ensure_user(db, type("U", (), {"id": user_id, "first_name": first_name}))
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            raise ValueError(f"Пользователь {user_id} не найден после создания")
        return dict(row)
    except aiosqlite.Error as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        raise

async def save_active_order(
    db: aiosqlite.Connection, user_id: int, dishes: list[tuple[str, int]], tag: Optional[str]
) -> None:
    """
    Сохраняет активный заказ пользователя в базу данных.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        dishes: Список блюд в формате [(название, крестики), ...]
        tag: Тег специального заказа ("critic", "student", "dirty_plate", None)
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
        json.JSONEncodeError: При ошибках сериализации данных
    """
    try:
        payload = {"dishes": dishes, "tag": tag}
        await db.execute(
            "UPDATE users SET active_order_json=? WHERE user_id=?",
            (json.dumps(payload, ensure_ascii=False), user_id),
        )
        await db.commit()
    except (aiosqlite.Error, json.JSONEncodeError) as e:
        logger.error(f"Ошибка сохранения активного заказа для пользователя {user_id}: {e}")
        raise


async def get_active_order(db: aiosqlite.Connection, user_id: int) -> Optional[dict]:
    """
    Получает активный заказ пользователя из базы данных.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        
    Returns:
        Словарь с данными заказа {"dishes": [...], "tag": ...} или None
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
        json.JSONDecodeError: При ошибках десериализации данных
    """
    try:
        cur = await db.execute("SELECT active_order_json FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row or not row["active_order_json"]:
            return None
        payload = json.loads(row["active_order_json"])
        return {
            "dishes": payload.get("dishes", []),
            "tag": payload.get("tag"),
        }
    except (aiosqlite.Error, json.JSONDecodeError) as e:
        logger.error(f"Ошибка получения активного заказа для пользователя {user_id}: {e}")
        raise


async def clear_active_order(db: aiosqlite.Connection, user_id: int) -> None:
    """
    Очищает активный заказ пользователя.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
    """
    try:
        await db.execute("UPDATE users SET active_order_json=NULL WHERE user_id=?", (user_id,))
        await db.commit()
    except aiosqlite.Error as e:
        logger.error(f"Ошибка очистки активного заказа для пользователя {user_id}: {e}")
        raise

async def save_last_order(
    db: aiosqlite.Connection,
    user_id: int,
    dishes: list[tuple[str, int]],
    order_crosses: int,
    tag: Optional[str] = None,
) -> None:
    """
    Сохраняет последний завершенный заказ для использования в событии "грязная тарелка".
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        dishes: Список блюд в формате [(название, крестики), ...]
        order_crosses: Общее количество крестиков в заказе
        tag: Тег специального заказа (опционально)
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
        json.JSONEncodeError: При ошибках сериализации данных
    """
    try:
        payload = {"dishes": dishes, "crosses": order_crosses, "tag": tag}
        await db.execute(
            "UPDATE users SET last_order_json=? WHERE user_id=?",
            (json.dumps(payload, ensure_ascii=False), user_id),
        )
        await db.commit()
    except (aiosqlite.Error, json.JSONEncodeError) as e:
        logger.error(f"Ошибка сохранения последнего заказа для пользователя {user_id}: {e}")
        raise


async def get_last_order(db: aiosqlite.Connection, user_id: int) -> Optional[dict]:
    """
    Получает последний завершенный заказ пользователя.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        
    Returns:
        Словарь с данными последнего заказа или None
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
        json.JSONDecodeError: При ошибках десериализации данных
    """
    try:
        cur = await db.execute("SELECT last_order_json FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row or not row["last_order_json"]:
            return None
        return json.loads(row["last_order_json"])
    except (aiosqlite.Error, json.JSONDecodeError) as e:
        logger.error(f"Ошибка получения последнего заказа для пользователя {user_id}: {e}")
        raise

async def finish_order_and_level(
    db: aiosqlite.Connection, user_id: int, tag: Optional[str], order_crosses: int
) -> tuple[int, bool, str, int]:
    """
    Завершает заказ и обновляет статистику пользователя.
    
    Увеличивает счетчик заказов, обновляет уровень при необходимости,
    сохраняет флаги специальных событий и последний заказ.
    
    Args:
        db: Подключение к базе данных
        user_id: Telegram ID пользователя
        tag: Тег специального заказа ("critic", "student", "dirty_plate", "second_chef", None)
        order_crosses: Количество крестиков в завершенном заказе
    
    Returns:
        Кортеж (total_orders, level_changed, title, total_crosses):
        - total_orders: Общее количество завершенных заказов
        - level_changed: True если уровень изменился
        - title: Название нового уровня
        - total_crosses: Общее количество накопленных крестиков
        
    Raises:
        aiosqlite.Error: При ошибках выполнения SQL-запроса
        json.JSONDecodeError: При ошибках десериализации данных
    """
    try:
        cur = await db.execute(
            """SELECT total_orders, total_crosses, level, has_student_done, 
                      has_dirty_plate_done, has_critic_done, has_second_chef_done, 
                      active_order_json 
               FROM users WHERE user_id=?""",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            raise ValueError(f"Пользователь {user_id} не найден")
            
        total = (row["total_orders"] or 0) + 1
        total_crosses = (row["total_crosses"] or 0) + order_crosses
        level = row["level"] or 0
        has_student_done = row["has_student_done"] or 0
        has_dirty_plate_done = row["has_dirty_plate_done"] or 0
        has_critic_done = row["has_critic_done"] or 0
        has_second_chef_done = row["has_second_chef_done"] or 0

        # Обновляем флаги специальных событий
        if tag == "critic":
            has_critic_done = 1
        elif tag == "student":
            has_student_done = 1
        elif tag == "dirty_plate":
            has_dirty_plate_done = 1
        elif tag == "second_chef":
            has_second_chef_done = 1

        # Сохраняем последний заказ для грязной тарелки
        active_order_data = row["active_order_json"]
        if active_order_data:
            try:
                payload = json.loads(active_order_data)
                dishes = payload.get("dishes", [])
                if dishes:  # Сохраняем только если есть блюда
                    await save_last_order(db, user_id, dishes, order_crosses, tag)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Не удалось сохранить последний заказ для {user_id}: {e}")

        prev_level = level
        if total % ORDERS_PER_LEVEL == 0 and level < MAX_LEVEL:
            level += 1

        await db.execute(
            """UPDATE users SET total_orders=?, total_crosses=?, level=?, 
                      has_student_done=?, has_dirty_plate_done=?, has_critic_done=?, 
                      has_second_chef_done=?, active_order_json=NULL 
               WHERE user_id=?""",
            (
                total,
                total_crosses,
                level,
                has_student_done,
                has_dirty_plate_done,
                has_critic_done,
                has_second_chef_done,
                user_id,
            ),
        )
        await db.commit()

        level_changed = level != prev_level
        title = LEVELS.get(level, f"Уровень {level}")

        return total, level_changed, title, total_crosses
    except (aiosqlite.Error, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Ошибка завершения заказа для пользователя {user_id}: {e}")
        raise
