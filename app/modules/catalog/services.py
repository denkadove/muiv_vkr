"""Сервисный слой каталога: бизнес-логика, независимая от HTTP."""

import os
import urllib.request
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
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    mp_statuses = getattr(form, "marketplace_statuses", None)
    mp_lines = mp_statuses.data if mp_statuses is not None else []

    composition = getattr(form, "composition", None)
    lines = composition.data if composition is not None else []
    if not lines:
        raise ValueError("Товар должен состоять хотя бы из одного примитива.")

    barcode = form.barcode.data.strip() if form.barcode.data else None
    product = Product(
        name=form.name.data,
        sku=form.sku.data.strip() if form.sku.data else None,
        barcode=int(barcode) if barcode else None,
        selling_price=form.selling_price.data,
        weight=form.weight.data,
        length=form.length.data,
        width=form.width.data,
        height=form.height.data,
        brand=form.brand.data.strip() if form.brand.data else None,
        country=form.country.data.strip() if form.country.data else None,
        warranty=form.warranty.data.strip() if form.warranty.data else None,
        video_url=form.video_url.data.strip() if form.video_url.data else None,
        active=form.active.data,
        description=form.description.data,
        category_id=category.id,
    )
    db.session.add(product)
    db.session.flush()

    # Загрузка фото
    from flask import current_app, request
    import os, uuid
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    allowed_ext = {"png", "jpg", "jpeg", "gif", "webp"}
    files = request.files.getlist("images") if request.files else []
    for i, f in enumerate(files[:10]):
        if not f or not f.filename:
            continue
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed_ext:
            continue
        filename = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(upload_dir, filename))
        db.session.add(ProductImage(product_id=product.id, filename=filename, is_main=(i == 0), sort_order=i))

    # Загрузка сертификата
    cert = request.files.get("certificate") if request.files else None
    if cert and cert.filename:
        ext = cert.filename.rsplit(".", 1)[-1].lower() if "." in cert.filename else ""
        if ext in {"pdf", "png", "jpg", "jpeg"}:
            filename = f"{uuid.uuid4().hex}.{ext}"
            cert.save(os.path.join(upload_dir, filename))
            product.certificate = filename

    for line in mp_lines:
        mp_id = line.get("marketplace_id") if isinstance(line, dict) else getattr(line, "marketplace_id", None)
        status = line.get("status") if isinstance(line, dict) else getattr(line, "status", None)
        if not mp_id:
            continue
        db.session.add(ProductMarketplace(product_id=product.id, marketplace_id=int(mp_id), status=status or "x"))

    for line in lines:
        primitive_id = line.get("primitive_id") if isinstance(line, dict) else getattr(line, "primitive_id", None)
        quantity = line.get("quantity") if isinstance(line, dict) else getattr(line, "quantity", None)
        if not primitive_id:
            continue
        primitive = db.session.get(Primitive, int(primitive_id))
        if primitive is None:
            raise ValueError("Указан несуществующий примитив.")
        qty = int(quantity or 1)
        if qty < 1:
            raise ValueError("Количество примитива должно быть не меньше 1.")
        db.session.execute(
            product_primitives.insert().values(
                product_id=product.id, primitive_id=primitive.id, quantity=qty
            )
        )

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

    mp_statuses = getattr(form, "marketplace_statuses", None)
    mp_lines = mp_statuses.data if mp_statuses is not None else []

    product.name = form.name.data
    product.active = form.active.data
    product.sku = form.sku.data.strip() if form.sku.data else None
    product.barcode = int(form.barcode.data.strip()) if form.barcode.data and form.barcode.data.strip() else None
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
    product.category_id = category.id

    # Загрузка новых фото
    from flask import current_app, request
    import os, uuid
    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(upload_dir, exist_ok=True)
    allowed_ext = {"png", "jpg", "jpeg", "gif", "webp"}
    files = request.files.getlist("images") if request.files else []
    existing_count = ProductImage.query.filter_by(product_id=product.id).count() if False else len(product.images)
    for i, f in enumerate(files):
        if existing_count + i >= 10:
            break
        if not f or not f.filename:
            continue
        ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in allowed_ext:
            continue
        filename = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(upload_dir, filename))
        db.session.add(ProductImage(product_id=product.id, filename=filename, is_main=(len(product.images) == 0), sort_order=len(product.images)))

    # Загрузка сертификата (заменяет старый)
    cert = request.files.get("certificate") if request.files else None
    if cert and cert.filename:
        ext = cert.filename.rsplit(".", 1)[-1].lower() if "." in cert.filename else ""
        if ext in {"pdf", "png", "jpg", "jpeg"}:
            filename = f"{uuid.uuid4().hex}.{ext}"
            cert.save(os.path.join(upload_dir, filename))
            product.certificate = filename

    # Обновляем связи с маркетплейсами
    ProductMarketplace.query.filter_by(product_id=product.id).delete()
    for line in mp_lines:
        mp_id = line.get("marketplace_id") if isinstance(line, dict) else getattr(line, "marketplace_id", None)
        status = line.get("status") if isinstance(line, dict) else getattr(line, "status", None)
        if not mp_id:
            continue
        db.session.add(ProductMarketplace(product_id=product.id, marketplace_id=int(mp_id), status=status or "x"))

    # Обновляем состав
    db.session.execute(
        product_primitives.delete().where(product_primitives.c.product_id == product.id)
    )
    composition = getattr(form, "composition", None)
    lines = composition.data if composition is not None else []
    if not lines:
        raise ValueError("Товар должен состоять хотя бы из одного примитива.")
    for line in lines:
        primitive_id = line.get("primitive_id") if isinstance(line, dict) else getattr(line, "primitive_id", None)
        quantity = line.get("quantity") if isinstance(line, dict) else getattr(line, "quantity", None)
        if not primitive_id:
            continue
        primitive = db.session.get(Primitive, int(primitive_id))
        if primitive is None:
            raise ValueError("Указан несуществующий примитив.")
        qty = int(quantity or 1)
        if qty < 1:
            raise ValueError("Количество примитива должно быть не меньше 1.")
        db.session.execute(
            product_primitives.insert().values(
                product_id=product.id, primitive_id=primitive.id, quantity=qty
            )
        )

    db.session.commit()
    cleanup_unused_primitives()
    return product


def delete_product(product_id: int) -> None:
    """Удаляет товар и очищает неиспользуемые примитивы."""
    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    db.session.delete(product)
    db.session.commit()
    cleanup_unused_primitives()


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


def cleanup_unused_primitives() -> None:
    """Удаляет примитивы, не используемые ни в одном товаре."""
    unused = Primitive.query.filter(~Primitive.products.any()).all()
    for p in unused:
        db.session.delete(p)
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

    urllib.request.urlretrieve(feed_url, file_path)

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
        name = get("name") or ""
        sku = str(offer_id) if offer_id else str(product_id)

        price_004_usd = _to_float(get("price_004_usd"))

        remainder_tp = _to_int(get("remainder_ism_spb_tp_73"))
        remainder_tp_reserve = _to_int(get("remainder_ism_spb_tp_reserve_73"))

        primitive = Primitive.query.filter_by(sku=sku).first()
        is_new = primitive is None
        if is_new:
            primitive = Primitive(sku=sku)
            db.session.add(primitive)

        primitive.site_id = product_id
        primitive.product_id = product_id
        primitive.name = name
        primitive.url = get("url")
        primitive.price_208_rub = _to_float(get("price_208_rub"))
        primitive.price_208_usd = _to_float(get("price_208_usd"))
        primitive.price_213_rub = _to_float(get("price_213_rub"))
        primitive.price_213_usd = _to_float(get("price_213_usd"))
        primitive.price_004_rub = _to_float(get("price_004_rub"))
        primitive.price_004_usd = price_004_usd
        primitive.update_price_only = get("update_price_only") == "true"
        primitive.update_stock_only = get("update_stock_only") == "true"
        primitive.remainder_ism_spb_tp_73 = remainder_tp
        primitive.remainder_ism_spb_tp_reserve_73 = remainder_tp_reserve
        primitive.remainder_msk_salarevo_278 = _to_int(get("remainder_msk_salarevo_278"))
        primitive.remainder_msk_salarevo_reserve_278 = _to_int(get("remainder_msk_salarevo_reserve_278"))
        primitive.remainder_osha_spb_tp_305 = _to_int(get("remainder_osha_spb_tp_305"))
        primitive.remainder_osha_spb_tp_reserve_305 = _to_int(get("remainder_osha_spb_tp_reserve_305"))
        primitive.remainder_svh_179 = _to_int(get("remainder_svh_179"))
        primitive.remainder_svh_reserve_179 = _to_int(get("remainder_svh_reserve_179"))
        primitive.remainder_bsho_spb_tp_2 = _to_int(get("remainder_bsho_spb_tp_2"))
        primitive.remainder_bsho_spb_tp_reserve_2 = _to_int(get("remainder_bsho_spb_tp_reserve_2"))
        primitive.price = price_004_usd
        primitive.updated_at = datetime.now(timezone.utc)
        if is_new:
            primitive.created_at = datetime.now(timezone.utc)
            created += 1
        else:
            updated += 1

    db.session.commit()
    return created, updated, file_path