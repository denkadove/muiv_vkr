"""Модели каталога: категории, товары, маркетплейсы, примитивы."""

from datetime import datetime, timezone

from app.extensions import db


class Category(db.Model):
    """Категория товара."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    processing_cost = db.Column(db.Numeric(10, 2), default=0)
    coinvest_factor = db.Column(db.Numeric(5, 2), default=0.5)
    products = db.relationship("Product", backref="category")


class ProductMarketplace(db.Model):
    """Связь товара и маркетплейса со статусом размещения."""

    __tablename__ = "product_marketplaces"

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), primary_key=True)
    marketplace_id = db.Column(db.Integer, db.ForeignKey("marketplaces.id"), primary_key=True)
    status = db.Column(db.String(10), nullable=False, default="x")

    product = db.relationship("Product", back_populates="marketplace_links")
    marketplace = db.relationship("Marketplace", back_populates="product_links")

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
    sku = db.Column(db.String(255), unique=True, nullable=True)
    name = db.Column(db.String(255), nullable=False)
    barcode = db.Column(db.BigInteger, nullable=True)
    selling_price = db.Column(db.Numeric(10, 2), nullable=True)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    marketplace_links = db.relationship("ProductMarketplace", back_populates="product", cascade="all, delete-orphan")
    primitives = db.relationship(
        "Primitive",
        secondary=product_primitives,
        backref="products",
    )
    # UTC
    created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def cost_price(self):
        """Цена входа: сумма цен примитивов с учётом количества."""
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

    def _warehouse_stock(self, attr: str) -> int:
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
            prim_stock = getattr(primitive, attr, 0)
            values.append(prim_stock // qty if qty else 0)
        return min(values) if values else 0

    @property
    def stock_spb_tp(self):
        return self._warehouse_stock("stock_spb_tp")

    @property
    def stock_msk(self):
        return self._warehouse_stock("stock_msk")

    @property
    def stock_spb_osh(self):
        return self._warehouse_stock("stock_spb_osh")

    @property
    def stock_spb_svh(self):
        return self._warehouse_stock("stock_spb_svh")

    @property
    def stock_spb_bsho(self):
        return self._warehouse_stock("stock_spb_bsho")

    @property
    def marketplaces(self):
        return [link.marketplace for link in self.marketplace_links]

    def marketplace_status(self, marketplace_id):
        for link in self.marketplace_links:
            if link.marketplace_id == marketplace_id:
                return link.status
        return None

    @property
    def marketplace_status_map(self):
        result = {}
        for link in self.marketplace_links:
            if link.marketplace:
                result[link.marketplace.short_name or link.marketplace.name] = link.status
        return result


class Marketplace(db.Model):
    """Маркетплейсы."""

    __tablename__ = "marketplaces"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    short_name = db.Column(db.String(50), nullable=True)
    marketplace_type = db.Column(db.String(50), nullable=False, default="Яндекс")
    description = db.Column(db.Text)
    api_key = db.Column(db.String(255), nullable=True, unique=True)
    product_links = db.relationship("ProductMarketplace", back_populates="marketplace", cascade="all, delete-orphan")


class Primitive(db.Model):
    """Примитив — составная часть товара (может импортироваться из фида)."""

    __tablename__ = "primitives"

    id = db.Column(db.Integer, primary_key=True)
    # sku = offer_id из фида, уникальный в нашей системе
    sku = db.Column(db.String(255), unique=True, nullable=False)
    # product_id из фида (site_id), не уникальный
    site_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(255), nullable=False)
    # Основное поле (вычисляется из фида)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    # Поля из фида
    product_id = db.Column(db.Integer, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    price_208_rub = db.Column(db.Numeric(10, 2), nullable=True)
    price_208_usd = db.Column(db.Numeric(10, 2), nullable=True)
    price_213_rub = db.Column(db.Numeric(10, 2), nullable=True)
    price_213_usd = db.Column(db.Numeric(10, 2), nullable=True)
    price_004_rub = db.Column(db.Numeric(10, 2), nullable=True)
    price_004_usd = db.Column(db.Numeric(10, 2), nullable=True)
    update_price_only = db.Column(db.Boolean, default=False)
    update_stock_only = db.Column(db.Boolean, default=False)
    # Остатки по складам
    remainder_ism_spb_tp_73 = db.Column(db.Integer, default=0)
    remainder_ism_spb_tp_reserve_73 = db.Column(db.Integer, default=0)
    remainder_msk_salarevo_278 = db.Column(db.Integer, default=0)
    remainder_msk_salarevo_reserve_278 = db.Column(db.Integer, default=0)
    remainder_osha_spb_tp_305 = db.Column(db.Integer, default=0)
    remainder_osha_spb_tp_reserve_305 = db.Column(db.Integer, default=0)
    remainder_svh_179 = db.Column(db.Integer, default=0)
    remainder_svh_reserve_179 = db.Column(db.Integer, default=0)
    remainder_bsho_spb_tp_2 = db.Column(db.Integer, default=0)
    remainder_bsho_spb_tp_reserve_2 = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def stock_spb_tp(self):
        return max(0, self.remainder_ism_spb_tp_73 - self.remainder_ism_spb_tp_reserve_73)

    @property
    def stock_msk(self):
        return max(0, self.remainder_msk_salarevo_278 - self.remainder_msk_salarevo_reserve_278)

    @property
    def stock_spb_osh(self):
        return max(0, self.remainder_osha_spb_tp_305 - self.remainder_osha_spb_tp_reserve_305)

    @property
    def stock_spb_svh(self):
        return max(0, self.remainder_svh_179 - self.remainder_svh_reserve_179)

    @property
    def stock_spb_bsho(self):
        return max(0, self.remainder_bsho_spb_tp_2 - self.remainder_bsho_spb_tp_reserve_2)