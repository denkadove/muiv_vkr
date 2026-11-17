"""Сервисы настроек приложения."""

from app.extensions import db
from app.modules.settings.models import Setting


def get_setting(key: str, default: str | None = None) -> str | None:
    setting = db.session.get(Setting, key)
    return setting.value if setting else default


def set_setting(key: str, value: str | None) -> None:
    setting = db.session.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    db.session.commit()