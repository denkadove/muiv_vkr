"""Модели базы данных."""

from datetime import datetime, timezone

from flask_login import UserMixin

from app import db

# Группа 1 — администратор, группа 2 — обычный пользователь
ADMIN_GROUP_ID: int = 1
USER_GROUP_ID: int = 2


class UserGroup(db.Model):
    """Группа пользователей, определяет права доступа."""

    __tablename__ = "user_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class User(UserMixin, db.Model):
    """Пользователь системы: вход в систему и профиль."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255), unique=True)
    # Пароль хранится только в виде bcrypt-хэша
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey("user_groups.id"), nullable=True)
    group = db.relationship("UserGroup", backref="users")
    # UTC; lambda — чтобы время фиксировалось при вставке, а не при старте
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        """Признак активности учётной записи для flask-login.

        Особенности:
            - перекрывает всегда-True значение UserMixin;
            - flask-login сам не пускает и разлогинивает неактивных.

        Возвращает:
            bool: True, если учётная запись активна.
        """
        return bool(self.active)
