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

    # Настройки почты (для восстановления пароля)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "1025"))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@example.com")
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"

    # Константы перенесены в app/modules/settings/constants.py