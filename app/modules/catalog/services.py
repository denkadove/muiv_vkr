"""Сервисный слой каталога: бизнес-логика, независимая от HTTP."""

import os
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.modules.catalog.forms import CategoryForm, MarketplaceForm, ProductForm
from app.modules.settings.constants import DEFAULT_CATEGORY_NAME
from app.modules.catalog.models import (
    Category,
    Marketplace,
    Primitive,
    Product,
    ProductImage,
    ProductMarketplace,
    product_primitives,
)

MAX_PRODUCT_IMAGES = 10
MAX_FEED_SIZE = 50 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_CERT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


def _upload_dir() -> str:
    """Возвращает директорию загрузок товара (создаёт её при необходимости)."""
    from flask import current_app

    path = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(path, exist_ok=True)
    return path


def _save_product_images(product_id: int, files, existing_count: int = 0) -> None:
    """Сохраняет новые фото товара, не превышая лимит и сохраняя порядок."""
    for file in files:
        if existing_count >= MAX_PRODUCT_IMAGES:
            break
        if not file or not file.filename:
            continue
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            continue
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(_upload_dir(), filename))
        db.session.add(ProductImage(
            product_id=product_id,
            filename=filename,
            is_main=(existing_count == 0),
            sort_order=existing_count,
        ))
        existing_count += 1


def _save_certificate(product: Product, certificate) -> None:
    """Сохраняет сертификат, если он был загружен."""
    if not certificate or not certificate.filename:
        return
    ext = certificate.filename.rsplit(".", 1)[-1].lower() if "." in certificate.filename else ""
    if ext not in ALLOWED_CERT_EXTENSIONS:
        return
    filename = f"{uuid.uuid4().hex}.{ext}"
    certificate.save(os.path.join(_upload_dir(), filename))
    product.certificate = filename


def _form_lines(form, field: str) -> list:
    """Возвращает строки FieldList формы (или пустой список)."""
    container = getattr(form, field, None)
    return container.data if container is not None else []


def _line_value(line, field: str):
    """Читает поле строки формы независимо от её типа."""
    return line.get(field) if isinstance(line, dict) else getattr(line, field, None)


def _apply_product_fields(product: Product, form: ProductForm, category: Category) -> None:
    """Переносит общие поля формы в товар."""
    barcode = form.barcode.data.strip() if form.barcode.data else ""
    product.name = form.name.data
    product.sku = form.sku.data.strip() if form.sku.data else None
    product.barcode = int(barcode) if barcode else None
    product.selling_price = form.selling_price.data
    product.weight = form.weight.data
    product.length = form.length.data
    product.width = form.width.data
    product.height = form.height.data
    product.brand = form.brand.data.strip() if form.brand.data else None
    product.country = form.country.data.strip() if form.country.data else None
    product.warranty = form.warranty.data.strip() if form.warranty.data else None
    product.video_url = form.video_url.data.strip() if form.video_url.data else None
    product.description = form.description.data
    product.active = form.active.data
    product.category_id = category.id


def _sync_marketplace_links(product_id: int, lines: list) -> None:
    """Полностью пересоздаёт связи товара с маркетплейсами."""
    ProductMarketplace.query.filter_by(product_id=product_id).delete()
    for line in lines:
        mp_id = _line_value(line, "marketplace_id")
        if not mp_id:
            continue
        db.session.add(ProductMarketplace(
            product_id=product_id,
            marketplace_id=int(mp_id),
            status=_line_value(line, "status") or "x",
        ))


def _sync_composition(product_id: int, lines: list) -> None:
    """Полностью пересоздаёт состав товара."""
    if not lines:
        raise ValueError("Товар должен состоять хотя бы из одного примитива.")
    db.session.execute(
        product_primitives.delete().where(product_primitives.c.product_id == product_id)
    )
    for line in lines:
        primitive_id = _line_value(line, "primitive_id")
        if not primitive_id:
            continue
        primitive = db.session.get(Primitive, int(primitive_id))
        if primitive is None:
            raise ValueError("Указан несуществующий примитив.")
        qty = int(_line_value(line, "quantity") or 1)
        if qty < 1:
            raise ValueError("Количество примитива должно быть не меньше 1.")
        db.session.execute(
            product_primitives.insert().values(
                product_id=product_id, primitive_id=primitive.id, quantity=qty
            )
        )


def get_categories() -> list[Category]:
    """Возвращает список категорий в порядке создания."""
    if Category.query.count() == 0:
        db.session.add(Category(name=DEFAULT_CATEGORY_NAME))
        db.session.commit()
    return Category.query.order_by(Category.sort_order, Category.id).all()


def create_category(form: CategoryForm) -> Category:
    """Создаёт категорию."""
    if Category.query.filter_by(name=form.name.data).first() is not None:
        raise ValueError("Категория с таким названием уже существует.")

    category = Category(
        name=form.name.data,
        active=form.active.data,
        sort_order=form.sort_order.data or 0,
        processing_cost=form.processing_cost.data or 0,
        coinvest_factor=form.coinvest_factor.data or 0.5,
    )

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
    category.active = form.active.data
    category.sort_order = form.sort_order.data or 0
    category.processing_cost = form.processing_cost.data or 0
    category.coinvest_factor = form.coinvest_factor.data or 0.5
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
    from flask import request

    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    lines = _form_lines(form, "composition")
    if not lines:
        raise ValueError("Товар должен состоять хотя бы из одного примитива.")

    product = Product()
    _apply_product_fields(product, form, category)
    db.session.add(product)
    db.session.flush()

    files = request.files.getlist("images") if request.files else []
    _save_product_images(product.id, files)
    _save_certificate(product, request.files.get("certificate") if request.files else None)

    _sync_marketplace_links(product.id, _form_lines(form, "marketplace_statuses"))
    _sync_composition(product.id, lines)

    db.session.commit()
    return product


def update_product(product_id: int, form: ProductForm) -> Product:
    """Обновляет товар."""
    from flask import request

    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    lines = _form_lines(form, "composition")
    if not lines:
        raise ValueError("Товар должен состоять хотя бы из одного примитива.")

    _apply_product_fields(product, form, category)

    files = request.files.getlist("images") if request.files else []
    existing_count = ProductImage.query.filter_by(product_id=product.id).count()
    _save_product_images(product.id, files, existing_count=existing_count)
    _save_certificate(product, request.files.get("certificate") if request.files else None)

    _sync_marketplace_links(product.id, _form_lines(form, "marketplace_statuses"))
    _sync_composition(product.id, lines)

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
        marketplace_type=form.marketplace_type.data,
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
    marketplace.marketplace_type = form.marketplace_type.data
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


def get_primitives() -> list[Primitive]:
    """Возвращает список примитивов."""
    return Primitive.query.order_by(Primitive.id).all()


def create_primitive(form) -> Primitive:
    """Создаёт примитив."""
    if Primitive.query.filter_by(sku=form.sku.data).first() is not None:
        raise ValueError("Примитив с таким артикулом уже существует.")

    primitive = Primitive(
        sku=form.sku.data,
        name=form.name.data,
        price=form.price.data,
    )
    db.session.add(primitive)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Примитив с таким артикулом уже существует.")
    return primitive


def update_primitive(primitive_id: int, form) -> Primitive:
    """Обновляет примитив."""
    primitive: Primitive | None = db.session.get(Primitive, primitive_id)
    if primitive is None:
        raise LookupError("Примитив не найден.")

    if Primitive.query.filter(Primitive.sku == form.sku.data, Primitive.id != primitive_id).first() is not None:
        raise ValueError("Примитив с таким артикулом уже существует.")

    primitive.sku = form.sku.data
    primitive.name = form.name.data
    primitive.price = form.price.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Примитив с таким артикулом уже существует.")
    return primitive


def delete_primitive(primitive_id: int) -> None:
    """Удаляет примитив, если он не используется в товарах."""
    primitive: Primitive | None = db.session.get(Primitive, primitive_id)
    if primitive is None:
        raise LookupError("Примитив не найден.")

    used_in = Product.query.filter(Product.primitives.any(id=primitive_id)).first()
    if used_in is not None:
        raise ValueError("Нельзя удалить примитив, используемый в товарах.")

    db.session.delete(primitive)
    db.session.commit()


def _to_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


PRICE_FEED_FIELDS = {
    "price_208_rub": _to_float,
    "price_208_usd": _to_float,
    "price_213_rub": _to_float,
    "price_213_usd": _to_float,
    "price_004_rub": _to_float,
    "price_004_usd": _to_float,
}
STOCK_FEED_FIELDS = (
    "remainder_ism_spb_tp_73",
    "remainder_ism_spb_tp_reserve_73",
    "remainder_msk_salarevo_278",
    "remainder_msk_salarevo_reserve_278",
    "remainder_osha_spb_tp_305",
    "remainder_osha_spb_tp_reserve_305",
    "remainder_svh_179",
    "remainder_svh_reserve_179",
    "remainder_bsho_spb_tp_2",
    "remainder_bsho_spb_tp_reserve_2",
)


def _download_feed(feed_url: str, file_path: str) -> None:
    """Скачивает фид с ограничением размера и таймаутом."""
    parsed = urllib.parse.urlparse(feed_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Недопустимый URL фида: разрешены только http и https.")

    with urllib.request.urlopen(feed_url, timeout=30) as response:
        data = response.read(MAX_FEED_SIZE + 1)
    if len(data) > MAX_FEED_SIZE:
        raise ValueError("Фид слишком большой (более 50 МБ).")

    with open(file_path, "wb") as feed_file:
        feed_file.write(data)


def import_primitives_from_feed(feed_url: str) -> tuple[int, int, str]:
    """Скачивает фид, парсит и upsert-ит примитивы.

    Возвращает (created, updated, file_path).
    """
    if not feed_url:
        raise ValueError("URL фида не задан в настройках.")

    logs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "logs",
    )
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = os.path.join(logs_dir, f"{timestamp}_primitives.xml")

    _download_feed(feed_url, file_path)

    tree = ET.parse(file_path)
    root = tree.getroot()

    created = 0
    updated = 0

    for offer in root.iter("offer"):
        def get(tag):
            el = offer.find(tag)
            return el.text.strip() if el is not None and el.text else None

        offer_id = _to_int(get("offer_id"))
        product_id = _to_int(get("product_id"))
        if not offer_id and not product_id:
            continue
        sku = str(offer_id) if offer_id else str(product_id)

        price_only = get("update_price_only") == "true"
        stock_only = get("update_stock_only") == "true"

        primitive = Primitive.query.filter_by(sku=sku).first()
        is_new = primitive is None
        if is_new:
            primitive = Primitive(sku=sku)
            db.session.add(primitive)

        # Оба флага вместе или оба отсутствуют означают полное обновление.
        full_update = is_new or price_only == stock_only

        primitive.site_id = product_id
        primitive.product_id = product_id
        if full_update:
            primitive.name = get("name") or ""
            primitive.url = get("url")
            primitive.update_price_only = price_only
            primitive.update_stock_only = stock_only
        if full_update or price_only:
            for field, converter in PRICE_FEED_FIELDS.items():
                setattr(primitive, field, converter(get(field)))
            primitive.price = primitive.price_004_usd or 0
        if full_update or stock_only:
            for field in STOCK_FEED_FIELDS:
                setattr(primitive, field, _to_int(get(field)))
        primitive.updated_at = datetime.now(timezone.utc)
        if is_new:
            primitive.created_at = datetime.now(timezone.utc)
            created += 1
        else:
            updated += 1

    db.session.commit()
    return created, updated, file_path