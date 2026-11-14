"""Модели базы данных."""

from datetime import datetime, timezone

from flask_login import UserMixin

from app import db


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
    # Время создания в UTC; lambda нужна, чтобы время вычислялось при вставке,
    # а не при старте приложения
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
