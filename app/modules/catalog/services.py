"""Сервисный слой каталога: бизнес-логика, независимая от HTTP."""

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.catalog.forms import CategoryForm, MarketplaceForm, ProductForm
from app.modules.settings.constants import DEFAULT_CATEGORY_NAME
from app.modules.catalog.models import (
    Category,
    Marketplace,
    Product,
)


def get_categories() -> list[Category]:
    """Возвращает список категорий в порядке создания."""
    if Category.query.count() == 0:
        db.session.add(Category(name=DEFAULT_CATEGORY_NAME))
        db.session.commit()
    return Category.query.order_by(Category.id).all()


def create_category(form: CategoryForm) -> Category:
    """Создаёт категорию."""
    if Category.query.filter_by(name=form.name.data).first() is not None:
        raise ValueError("Категория с таким названием уже существует.")

    category = Category(name=form.name.data)

    db.session.add(category)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Категория с таким названием уже существует.")
    return category


def update_category(category_id: int, form: CategoryForm) -> Category:
    """Переименовывает категорию."""
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        raise LookupError("Категория не найдена.")
    if category.name == DEFAULT_CATEGORY_NAME:
        raise ValueError("Нельзя переименовать категорию «Без категории».")
    if (
        Category.query.filter(Category.name == form.name.data, Category.id != category_id)
        .first()
        is not None
    ):
        raise ValueError("Категория с таким названием уже существует.")

    category.name = form.name.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Категория с таким названием уже существует.")
    return category


def delete_category(category_id: int) -> None:
    """Удаляет категорию, перенося её товары в «Без категории»."""
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        raise LookupError("Категория не найдена.")
    if category.name == DEFAULT_CATEGORY_NAME:
        raise ValueError("Нельзя удалить категорию «Без категории».")

    default_category: Category | None = Category.query.filter_by(
        name=DEFAULT_CATEGORY_NAME
    ).first()
    if default_category is None:
        default_category = Category(name=DEFAULT_CATEGORY_NAME)
        db.session.add(default_category)
        db.session.flush()

    Product.query.filter_by(category_id=category_id).update(
        {"category_id": default_category.id}
    )
    db.session.delete(category)
    db.session.commit()


def create_product(form: ProductForm) -> Product:
    """Создаёт товар."""
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    marketplaces: list[Marketplace] = Marketplace.query.filter(
        Marketplace.id.in_(form.marketplaces.data or [])
    ).all()

    product = Product(
        name=form.name.data,
        price=form.price.data,
        marketplaces=marketplaces,
        description=form.description.data,
        category_id=category.id,
    )
    db.session.add(product)
    db.session.commit()
    return product


def update_product(product_id: int, form: ProductForm) -> Product:
    """Обновляет товар."""
    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    marketplaces: list[Marketplace] = Marketplace.query.filter(
        Marketplace.id.in_(form.marketplaces.data or [])
    ).all()

    product.marketplaces = marketplaces
    product.name = form.name.data
    product.price = form.price.data
    product.description = form.description.data
    product.category_id = category.id

    db.session.commit()
    return product


def delete_product(product_id: int) -> None:
    """Удаляет товар."""
    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    db.session.delete(product)
    db.session.commit()


def create_marketplace(form: MarketplaceForm) -> Marketplace:
    """Создаёт маркетплейс."""
    marketplace = Marketplace(
        name=form.name.data,
        api_key=form.api_key.data,
        description=form.description.data,
    )
    db.session.add(marketplace)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Маркетплейс с таким названием уже существует.")
    return marketplace


def update_marketplace(marketplace_id: int, form: MarketplaceForm) -> Marketplace:
    """Обновляет маркетплейс."""
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        raise LookupError("Маркетплейс не найден.")

    marketplace.name = form.name.data
    marketplace.api_key = form.api_key.data
    marketplace.description = form.description.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Маркетплейс с таким названием уже существует.")
    return marketplace


def delete_marketplace(marketplace_id: int) -> None:
    """Удаляет маркетплейс."""
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        raise LookupError("Маркетплейс не найден.")

    db.session.delete(marketplace)
    db.session.commit()