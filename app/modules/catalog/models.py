"""Модели каталога: категории, товары, маркетплейсы, примитивы."""

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

product_primitives = db.Table(
    "product_primitives",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id"), primary_key=True),
    db.Column("primitive_id", db.Integer, db.ForeignKey("primitives.id"), primary_key=True),
    db.Column("quantity", db.Integer, nullable=False, default=1),
)


class Product(db.Model):
    """Товар, состоящий из примитивов."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    marketplaces = db.relationship("Marketplace", secondary=product_marketplaces, backref="products")
    primitives = db.relationship(
        "Primitive",
        secondary=product_primitives,
        backref="products",
    )
    # UTC
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def price(self):
        """Сумма цен примитивов с учётом количества."""
        total = 0
        for primitive in self.primitives:
            # quantity хранится в association, но relationship не даёт прямой доступ;
            # используем запрос к таблице
            assoc = db.session.execute(
                product_primitives.select().where(
                    product_primitives.c.product_id == self.id,
                    product_primitives.c.primitive_id == primitive.id,
                )
            ).first()
            qty = assoc.quantity if assoc else 1
            total += float(primitive.price) * qty
        return round(total, 2)

    @property
    def stock(self):
        """Наименьший остаток среди примитивов с учётом количества."""
        if not self.primitives:
            return 0
        values = []
        for primitive in self.primitives:
            assoc = db.session.execute(
                product_primitives.select().where(
                    product_primitives.c.product_id == self.id,
                    product_primitives.c.primitive_id == primitive.id,
                )
            ).first()
            qty = assoc.quantity if assoc else 1
            values.append(primitive.stock // qty if qty else 0)
        return min(values) if values else 0


class Marketplace(db.Model):
    """Маркетплейсы."""

    __tablename__ = "marketplaces"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    api_key = db.Column(db.String(255), nullable=True, unique=True)


class Primitive(db.Model):
    """Примитив — составная часть товара."""

    __tablename__ = "primitives"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))