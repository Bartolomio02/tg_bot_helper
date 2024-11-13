from typing import Set
import os
import json
from pathlib import Path

class UserAccess:
    def __init__(self):
        """Ініціалізація системи контролю доступу користувачів"""
        self.blocked_users_file = Path("data/blocked_users.json")
        self._blocked_users: Set[int] = set()
        self._load_blocked_users()

    def _load_blocked_users(self) -> None:
        """Завантаження списку заблокованих користувачів з файлу"""
        try:
            if not self.blocked_users_file.exists():
                self.blocked_users_file.parent.mkdir(parents=True, exist_ok=True)
                self._save_blocked_users()
            else:
                with open(self.blocked_users_file, 'r') as f:
                    self._blocked_users = set(json.load(f))
        except Exception as e:
            print(f"Помилка при завантаженні списку заблокованих користувачів: {e}")
            self._blocked_users = set()

    def _save_blocked_users(self) -> None:
        """Збереження списку заблокованих користувачів у файл"""
        try:
            with open(self.blocked_users_file, 'w') as f:
                json.dump(list(self._blocked_users), f)
        except Exception as e:
            print(f"Помилка при збереженні списку заблокованих користувачів: {e}")

    def block_user(self, user_id: int) -> bool:
        """
        Блокування користувача
        
        :param user_id: ID користувача для блокування
        :return: True якщо користувача заблоковано, False якщо вже був заблокований
        """
        if user_id in self._blocked_users:
            return False
        self._blocked_users.add(user_id)
        self._save_blocked_users()
        return True

    def unblock_user(self, user_id: int) -> bool:
        """
        Розблокування користувача
        
        :param user_id: ID користувача для розблокування
        :return: True якщо користувача розблоковано, False якщо не був заблокований
        """
        if user_id not in self._blocked_users:
            return False
        self._blocked_users.remove(user_id)
        self._save_blocked_users()
        return True

    def is_blocked(self, user_id: int) -> bool:
        """
        Перевірка чи заблокований користувач
        
        :param user_id: ID користувача для перевірки
        :return: True якщо користувач заблокований, False якщо ні
        """
        return user_id in self._blocked_users

    def get_blocked_users(self) -> Set[int]:
        """
        Отримання списку всіх заблокованих користувачів
        
        :return: Множина ID заблокованих користувачів
        """
        return self._blocked_users.copy()

# Створюємо глобальний екземпляр для контролю доступу
user_access = UserAccess()
