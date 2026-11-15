"""Конфигурация приложения."""

import os


class Config:
    """Параметры приложения (подключается через from_object)."""

    # Название, отображается в шапке и заголовке страниц
    APP_NAME = "Консоль менеджера"
    # URI базы данных, переопределяется переменной окружения
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("SQLALCHEMY_DATABASE_URI") or "sqlite:///site.db"
    )
    # Ключ подписи сессий и CSRF
    # TODO: временный dev-ключ — в эксплуатации задавать переменной окружения
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-key-change-before-production"

    # Группа 1 — администратор, группа 2 — обычный пользователь
    ADMIN_GROUP_ID: int = 1
    USER_GROUP_ID: int = 2

    # Категория по умолчанию: сидится при первом запросе категорий, защищена от удаления
    DEFAULT_CATEGORY_NAME: str = "Без категории"

    GROUP_CHOICES: list[tuple[int, str]] = [
        (ADMIN_GROUP_ID, "Администратор"),
        (USER_GROUP_ID, "Пользователь"),
    ]

    CATEGORY_CHOICES: list[tuple[int, str]] = [
        (1, "Мелкогаборит"),
        (2, "Крупногабарит"),
    ]