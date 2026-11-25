"""Константы приложения (в будущем могут стать настройками из БД)."""

from typing import Final

# Группы пользователей
ADMIN_GROUP_ID: Final[int] = 1
USER_GROUP_ID: Final[int] = 2
MANAGER_GROUP_ID: Final[int] = 3

# Категория по умолчанию
DEFAULT_CATEGORY_NAME: Final[str] = "Без категории"

# Варианты выбора
GROUP_CHOICES: list[tuple[int, str]] = [
    (ADMIN_GROUP_ID, "Администратор"),
    (MANAGER_GROUP_ID, "Менеджер"),
    (USER_GROUP_ID, "Пользователь"),
]