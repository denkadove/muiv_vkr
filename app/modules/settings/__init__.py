"""Модуль настроек приложения (константы, в будущем — настройки из БД)."""

from flask import Blueprint

settings_bp = Blueprint("settings", __name__, template_folder="templates", url_prefix="/settings")

from . import routes