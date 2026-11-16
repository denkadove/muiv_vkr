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

    # Константы перенесены в app/modules/settings/constants.py