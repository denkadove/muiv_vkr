"""Конфигурация приложения."""

import os
import secrets


class Config:
    """Параметры приложения (подключается через from_object)."""

    # Название, отображается в шапке и заголовке страниц
    APP_NAME = "Консоль менеджера"
    # URI базы данных, переопределяется переменной окружения
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("SQLALCHEMY_DATABASE_URI") or "sqlite:///site.db"
    )
    # Ключ подписи сессий и CSRF. Без SECRET_KEY генерируется случайный ключ:
    # сессии сбрасываются при перезапуске, но в коде нет известного dev-ключа.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Константы перенесены в app/modules/settings/constants.py