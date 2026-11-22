"""Сервисы настроек приложения."""

from app.extensions import db
from app.modules.settings.models import Setting


def get_setting(key: str, default: str | None = None) -> str | None:
    setting = db.session.get(Setting, key)
    return setting.value if setting else default


def set_setting(key: str, value: str | float | None) -> None:
    """Сохраняет настройку; числовые значения хранятся строкой."""
    stored = None if value is None else str(value)
    setting = db.session.get(Setting, key)
    if setting is None:
        db.session.add(Setting(key=key, value=stored))
    else:
        setting.value = stored
    db.session.commit()


def get_float_setting(key: str, default: float | None = None) -> float | None:
    """Читает числовую настройку; возвращает default при пустом/битом значении."""
    raw = get_setting(key)
    if raw is None or raw == "":
        return default
    try:
        return float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return default
