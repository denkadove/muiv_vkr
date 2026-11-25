"""Модели пользователей и групп."""

from datetime import datetime, timezone

from flask_login import UserMixin

from app.extensions import db


class UserGroup(db.Model):
    """Группа пользователей, определяет права доступа."""

    __tablename__ = "user_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class User(UserMixin, db.Model):
    """Пользователь системы"""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True)
    # Пароль хранится только в виде bcrypt-хэша
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)
    group_id = db.Column(db.Integer, db.ForeignKey("user_groups.id"), nullable=True)
    group = db.relationship("UserGroup", backref="users")
    # Профиль
    name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    position = db.Column(db.String(255), nullable=True)
    department = db.Column(db.String(255), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)
    last_visit = db.Column(db.DateTime, nullable=True)
    # UTC; lambda — чтобы время фиксировалось при вставке, а не при старте
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        """Признак активности учётной записи для flask-login."""
        return bool(self.active)


class PasswordResetToken(db.Model):
    """Токен сброса пароля."""

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    used = db.Column(db.Boolean, default=False)

    user = db.relationship("User", backref="reset_tokens")