from datetime import datetime

import aiosqlite
import json
from typing import Dict, Any, Callable, Coroutine
from functools import lru_cache
import asyncio


class UsersData:
    """Клас для роботи з данними користувачів"""

    def __init__(self, db_file: str = "data/users_data.sqlite"):
        """Ініціалізація системи збереження данних користувачів"""
        self.db_file = db_file
        asyncio.run(self._initialize_db())

    async def _initialize_db(self) -> None:
        """Ініціалізація бази данних, якщо таблиці не існує
        date_created = день/місяць/рік
        uuid = date_created + id
        """

        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id TEXT NOT NULL,
                    date_created TEXT,
                    uuid TEXT,
                    name TEXT,
                    age INTEGER,
                    location TEXT,
                    event_details TEXT,
                    help_type TEXT,
                    description TEXT,
                    blocked BOOLEAN DEFAULT 0
                )
            ''')
            await db.commit()

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


    async def get_user_data(self, telegram_user_id: str) -> Dict[str, Any]:
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
                    # робимо словник з даних користувача
                    user_data = await cursor.fetchone()
                    if user_data is None:
                        return None
                    return {cursor.description[i][0]: user_data[i] for i in range(len(cursor.description))}
        except aiosqlite.Error as e:
            print(f"Помилка при отриманні данних користувача: {e}")
            return None


    async def get_user_data_by_uuid(self, uuid: str) -> Dict[str, Any]:
        """
        Отримання данних користувача по uuid
        :param uuid: uuid користувача
        :return: дані користувача
        """
        try:
            async with aiosqlite.connect(self.db_file) as db:
                async with db.execute('''
                    SELECT * FROM users
                    WHERE uuid = ?
                ''', (uuid,)) as cursor:
                    # робимо словник з даних користувача
                    user_data = await cursor.fetchone()
                    if user_data is None:
                        return None
                    return {cursor.description[i][0]: user_data[i] for i in range(len(cursor.description))}
        except aiosqlite.Error as e:
            print(f"Помилка при отриманні данних користувача: {e}")

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

    async def add_user(self, telegram_user_id: str) -> bool:
        """
        Додавання користувача
        :param telegram_user_id: ID користувача
        :return: True якщо користувача успішно додано, False якщо користувач вже існує

        """
        try:
            # перевірка чи користувач вже існує
            if await self.get_user_data(telegram_user_id) is not None:
                return False
            date_created = datetime.now().strftime('%d/%m/%Y')
            async with aiosqlite.connect(self.db_file) as db:
                await db.execute('''
                    INSERT INTO users (telegram_user_id, date_created)
                    VALUES (?, ?)
                ''', (str(telegram_user_id), str(date_created)))
                await db.commit()
            user_data = await self.get_user_data(telegram_user_id)
            await self.update_user_data(telegram_user_id, 'uuid', f'{date_created} {user_data["id"]}')
            return True

        except aiosqlite.Error as e:
            print(f"Помилка при додаванні користувача: {e}")
