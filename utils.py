"""
Модуль с общими утилитами для бота.

Содержит вспомогательные функции для форматирования сообщений
и проверки прав доступа.
"""
from config import ADMIN_IDS


def format_user_mention(user_id: int, first_name: str) -> str:
    """
    Форматирует имя пользователя как упоминание/гиперссылку для Telegram.
    
    Args:
        user_id: Telegram ID пользователя
        first_name: Имя пользователя
        
    Returns:
        HTML-строка с упоминанием пользователя (кликабельное имя)
        
    Example:
        >>> format_user_mention(123456, "Иван")
        "<a href='tg://user?id=123456'>Иван</a>"
    """
    return f"<a href='tg://user?id={user_id}'>{first_name}</a>"


def is_admin(user_id: str) -> bool:
    """
    Проверяет, является ли пользователь администратором бота.
    
    Args:
        user_id: Telegram ID пользователя (строка)
        
    Returns:
        True если пользователь является админом, иначе False
    """
    return str(user_id) in ADMIN_IDS
