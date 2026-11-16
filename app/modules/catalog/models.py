"""Модели каталога: категории, товары, маркетплейсы."""

from datetime import datetime, timezone

from app.extensions import db


class Category(db.Model):
    """Категория товара."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    products = db.relationship("Product", backref="category")


product_marketplaces = db.Table(
    "product_marketplaces",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
    db.Column("marketplace_id", db.Integer, db.ForeignKey("marketplaces.id"), primary_key=True),
)


class Product(db.Model):
    """Товар для размещения на маркетплейсах."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    marketplaces = db.relationship("Marketplace", secondary=product_marketplaces, backref="products")
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    # UTC; lambda — чтобы время фиксировалось при вставке, а не при старте
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Marketplace(db.Model):
    """Маркетплейсы."""

    __tablename__ = "marketplaces"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    api_key = db.Column(db.String(255), nullable=True, unique=True)