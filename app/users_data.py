import aiosqlite
import json
from typing import Dict, Any, Callable, Coroutine
from functools import lru_cache


class UsersData:
    """Клас для роботи з данними користувачів"""

    def __init__(self, db_file: str = "data/users_data.db"):
        """Ініціалізація системи збереження данних користувачів"""
        self.db_file = db_file

    async def _initialize_db(self) -> None:
        """Ініціалізація бази данних, якщо таблиці не існує
        date_created = день/місяць/рік
        uuid = date_created + id
        """

        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER AUTOINCREMENT,
                    telegram_user_id INTEGER PRIMARY KEY NOT NULL,
                    date_created TEXT default (strftime('%d-%m-%Y', 'now')),
                    uuid TEXT default (date_created || id),
                    name TEXT,
                    age INTEGER,
                    location TEXT,
                    event_details TEXT,
                    help_type TEXT,
                    description TEXT,
                    blocked BOOLEAN DEFAULT 0,
                )
            ''')
            await db.commit()

    def _ensure_initialized(self, func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        """Декоратор для гарантії ініціалізації бази даних"""

        async def wrapper(*args, **kwargs):
            await self._initialize_db()
            return await func(*args, **kwargs)

        return wrapper

    @_ensure_initialized
    async def update_user_data(self, telegram_user_id: int, field: str, value: Any) -> None:
        """
        Оновлення певного поля у користувача
        :param telegram_user_id: ID користувача
        :param field: поле для оновлення
        :param value: значення для оновлення
        """
        try:
            async with aiosqlite.connect(self.db_file) as db:
                await db.execute(f'''
                    UPDATE users
                    SET {field} = ?
                    WHERE telegram_user_id = ?
                ''', (value, telegram_user_id))
                await db.commit()
        except aiosqlite.Error as e:
            print(f"Помилка при оновленні данних користувача: {e}")

    @lru_cache(maxsize=5)
    @_ensure_initialized
    async def get_user_data(self, telegram_user_id: int) -> Dict[str, Any]:
        """
        Отримання данних користувача
        :param telegram_user_id: ID користувача
        :return: дані користувача
        """
        try:
            async with aiosqlite.connect(self.db_file) as db:
                async with db.execute('''
                    SELECT * FROM users
                    WHERE telegram_user_id = ?
                ''', (telegram_user_id,)) as cursor:
                    return await cursor.fetchone()
        except aiosqlite.Error as e:
            print(f"Помилка при отриманні данних користувача: {e}")
            return None

    @_ensure_initialized
    async def get_all_users_data(self) -> Dict[int, Dict[str, Any]]:
        """
        Отримання всіх данних користувачів
        :return: дані користувачів
        """
        try:
            async with aiosqlite.connect(self.db_file) as db:
                async with db.execute('''
                    SELECT * FROM users
                ''') as cursor:
                    return {user['telegram_user_id']: user for user in await cursor.fetchall()}
        except aiosqlite.Error as e:
            print(f"Помилка при отриманні всіх данних користувачів: {e}")
            return {}



