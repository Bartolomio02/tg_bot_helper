from typing import Any, Awaitable, Callable, Dict, List
from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache
from datetime import datetime
import os

def get_operator_ids() -> List[int]:
    """
    Отримання списку ID операторів з змінної середовища
    
    Формат OPERATOR_IDS: "id1,id2,id3" (через кому)
    """
    operator_ids_str = os.getenv('OPERATOR_IDS', '')
    if not operator_ids_str:
        return []
    try:
        return [int(op_id.strip()) for op_id in operator_ids_str.split(',') if op_id.strip()]
    except ValueError:
        return []

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        """
        Ініціалізація middleware для обмеження частоти повідомлень
        
        Використовує змінні середовища:
        RATE_LIMIT_MESSAGES: Максимальна кількість повідомлень за період (за замовчуванням 20)
        RATE_LIMIT_PERIOD: Період скидання обмежень у секундах (за замовчуванням 60)
        """
        # Отримуємо значення з змінних середовища або використовуємо значення за замовчуванням
        self.rate_limit = int(os.getenv('RATE_LIMIT_MESSAGES', 20))
        self.ttl_period = int(os.getenv('RATE_LIMIT_PERIOD', 60))
        
        # Кеш для зберігання лічильників повідомлень
        self.cache = TTLCache(maxsize=10000, ttl=self.ttl_period)
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обробка кожного повідомлення для перевірки обмежень
        
        :param handler: Обробник повідомлення
        :param event: Об'єкт повідомлення
        :param data: Додаткові дані
        :return: Результат обробки
        """
        # Отримуємо список ID операторів
        operator_ids = get_operator_ids()
        
        # Пропускаємо повідомлення від операторів
        if event.from_user.id in operator_ids:
            return await handler(event, data)

        user_id = event.from_user.id
        
        # Отримуємо поточний лічильник повідомлень користувача
        if user_id in self.cache:
            self.cache[user_id] += 1
        else:
            self.cache[user_id] = 1

        # Перевіряємо, чи не перевищено ліміт
        if self.cache[user_id] > self.rate_limit:
            await event.answer(
                "⚠️ <b>Ви надіслали забагато повідомлень.</b>\n"
                f"Будь ласка, зачекайте {self.ttl_period} секунд перед наступним повідомленням.",
                parse_mode="HTML"
            )
            return None

        return await handler(event, data)
