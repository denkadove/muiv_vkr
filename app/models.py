"""Модели базы данных."""
from datetime import datetime, timezone

from flask_login import UserMixin

from app import db

# Группа 1 — администратор, группа 2 — обычный пользователь
ADMIN_GROUP_ID: int = 1
USER_GROUP_ID: int = 2

# Категория по умолчанию: сидится при первом запросе категорий, защищена от удаления
DEFAULT_CATEGORY_NAME: str = "Без категории"


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


class Category(db.Model):
    """Категория товара."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    products = db.relationship("Product", backref="category")

product_marketplaces = db.Table('product_marketplaces',
    db.Column('product_id', db.Integer, db.ForeignKey('products.id'), primary_key=True),
    db.Column('marketplace_id', db.Integer, db.ForeignKey('marketplaces.id'), primary_key=True)
)

class Product(db.Model):
    """Товар для размещения на маркетплейсах."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    marketplaces = db.relationship('Marketplace', secondary=product_marketplaces, backref='products')
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    # UTC; lambda — чтобы время фиксировалось при вставке, а не при старте
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Marketplace(db.Model):
    """ Маркетплейсы """
    __tablename__ = "marketplaces"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    api_key = db.Column(db.String(255), nullable=True, unique=True)