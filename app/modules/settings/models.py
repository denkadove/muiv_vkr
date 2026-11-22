"""Модели настроек приложения."""

from app.extensions import db


class Setting(db.Model):
    """Настройка приложения (ключ-значение)."""

    __tablename__ = "settings"

    key = db.Column(db.String(255), primary_key=True)
    value = db.Column(db.Text, nullable=True)
    dollar_exchange_rate = db.Column(db.Float, nullable=True)
