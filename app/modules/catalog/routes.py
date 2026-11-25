"""Маршруты расширения «Каталог»: товары, категории, примитивы и магазины."""

from flask import Response, flash, redirect, render_template, request, url_for
from flask_sqlalchemy.pagination import Pagination

from app.extensions import db
from app.modules.auth.decorators import admin_required, manager_required
from app.modules.catalog import catalog_bp
from app.modules.catalog.forms import (
    CategoryForm,
    MarketplaceForm,
    PrimitiveForm,
    ProductForm,
)
from app.modules.catalog.integrations import OZON_MARKETPLACE_TYPE
from app.modules.catalog.ozon_import import import_ozon_data
from app.modules.catalog.models import (
    Category,
    Marketplace,
    Primitive,
    Product,
    ProductMarketplace,
    product_primitives,
)
from app.modules.catalog.services import (
    create_category,
    create_marketplace,
    create_primitive,
    create_product,
    delete_category,
    delete_marketplace,
    delete_primitive,
    delete_product,
    get_categories,
    get_primitives,
    import_primitives_from_feed,
    update_category,
    update_marketplace,
    update_primitive,
    update_product,
)
from app.modules.settings.services import get_setting

NO_STOCK_FIELDS = (
    "stock_spb_tp", "stock_msk", "stock_spb_osh", "stock_spb_svh", "stock_spb_bsho",
)


class _ListPagination(Pagination):
    """Пагинация по уже выбранному списку (фильтр «Без остатков»)."""

    def __init__(self, items: list, page: int, per_page: int = 20):
        self._items = items
        super().__init__(page=page, per_page=per_page, error_out=False, count=True)

    def _query_items(self) -> list:
        return self._items[self._query_offset:self._query_offset + self.per_page]

    def _query_count(self) -> int:
        return len(self._items)


def _paginate_items(items: list, page: int, per_page: int = 20) -> Pagination:
    return _ListPagination(items=items, page=page, per_page=per_page)


def _has_no_stock(item) -> bool:
    """Проверяет, что по всем складам нулевой остаток."""
    return all(getattr(item, field, 0) == 0 for field in NO_STOCK_FIELDS)


def _prepare_marketplace_statuses(form, marketplaces, product=None) -> None:
    """Заполняет статусы размещения при показе формы, не перезаписывая POST."""
    while len(form.marketplace_statuses.entries) > 0:
        form.marketplace_statuses.pop_entry()
    existing_links = (
        {link.marketplace_id: link for link in product.marketplace_links}
        if product is not None
        else {}
    )
    for marketplace in marketplaces:
        entry = form.marketplace_statuses.append_entry()
        entry.marketplace_id.data = marketplace.id
        entry.status.data = (
            product.marketplace_status(marketplace.id) if product else None
        ) or "x"
        link = existing_links.get(marketplace.id)
        entry.external_offer_id.data = link.external_offer_id if link else None


@catalog_bp.route("/products")
@manager_required
def products_list() -> str:
    tab = request.args.get("tab", "prices")
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    marketplace_id = request.args.get("marketplace_id", type=int)
    marketplace_status = request.args.get("marketplace_status", "").strip()
    no_stock = request.args.get("no_stock")
    active = request.args.get("active")

    query = Product.query
    if q:
        query = query.filter(
            (Product.name.ilike(f"%{q}%"))
            | (Product.sku.ilike(f"%{q}%"))
            | (Product.primitives.any(Primitive.sku.ilike(f"%{q}%")))
        )
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if marketplace_id:
        if marketplace_status:
            query = query.filter(Product.marketplace_links.any(
                (ProductMarketplace.marketplace_id == marketplace_id) &
                (ProductMarketplace.status == marketplace_status)
            ))
        else:
            query = query.filter(Product.marketplace_links.any(
                ProductMarketplace.marketplace_id == marketplace_id
            ))
    if active == "1":
        query = query.filter(Product.active.is_(True))

    page = request.args.get("page", 1, type=int)
    per_page = 20

    if no_stock == "1" and tab == "stock":
        all_products = query.order_by(Product.id).all()
        pagination = _paginate_items(
            [product for product in all_products if _has_no_stock(product)],
            page=page,
            per_page=per_page,
        )
    else:
        pagination = query.order_by(Product.id).paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items

    categories = get_categories()
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()
    ozon_marketplaces = [
        marketplace for marketplace in marketplaces
        if marketplace.marketplace_type == OZON_MARKETPLACE_TYPE
    ]
    return render_template("catalog/products.html", products=products, pagination=pagination,
                           categories=categories, marketplaces=marketplaces,
                           ozon_marketplaces=ozon_marketplaces,
                           ozon_type=OZON_MARKETPLACE_TYPE,
                           q=q, category_id=category_id, marketplace_id=marketplace_id,
                           marketplace_status=marketplace_status, no_stock=no_stock, active=active,
                           tab=tab)


@catalog_bp.route("/products/import-ozon", methods=["POST"])
@manager_required
def import_ozon() -> Response:
    """Импортирует цены и комиссии товаров из Ozon Seller API."""
    marketplace_id = request.form.get("marketplace_id", type=int)
    result = import_ozon_data(marketplace_id)
    flash(result.summary(), "success" if result.updated else "error")

    args = {"tab": "prices"}
    if marketplace_id is not None:
        args["marketplace_id"] = marketplace_id
    return redirect(url_for("catalog.products_list", **args))


@catalog_bp.route("/products/import-ozon-stock", methods=["POST"])
@manager_required
def import_ozon_stock() -> Response:
    """Импортирует остатки FBS товаров из Ozon Seller API."""
    from app.modules.catalog.ozon_import import import_ozon_stock as do_import

    marketplace_id = request.form.get("marketplace_id", type=int)
    result = do_import(marketplace_id)
    flash(result.summary(), "success" if result.updated else "error")

    args = {"tab": "stock"}
    if marketplace_id is not None:
        args["marketplace_id"] = marketplace_id
    return redirect(url_for("catalog.products_list", **args))


@catalog_bp.route("/products/create", methods=["GET", "POST"])
@manager_required
def product_create() -> Response | str:
    tab = request.args.get("tab", "main")
    form = ProductForm()
    form.category_id.choices = [(category.id, category.name) for category in get_categories()]

    marketplaces = Marketplace.query.order_by(Marketplace.name).all()
    if request.method == "GET":
        _prepare_marketplace_statuses(form, marketplaces)

    primitives = get_primitives()

    if form.validate_on_submit():
        try:
            create_product(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/product_form.html", form=form, primitives=primitives, marketplaces=marketplaces, tab=tab)

        flash(f"Товар {form.name.data} создан.", "success")
        return redirect(url_for("catalog.products_list", tab=tab))

    return render_template("catalog/product_form.html", form=form, primitives=primitives, marketplaces=marketplaces, tab=tab)


@catalog_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@manager_required
def product_edit(product_id: int) -> Response | str:
    tab = request.args.get("tab", "main")
    product: Product | None = db.session.get(Product, product_id)
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()

    if product is None:
        flash("Товар не найден.", "error")
        return redirect(url_for("catalog.products_list"))

    form = ProductForm(obj=product)
    if request.method == "GET":
        _prepare_marketplace_statuses(form, marketplaces, product=product)
        while len(form.composition.entries) > 0:
            form.composition.pop_entry()
        for p in product.primitives:
            assoc = db.session.execute(
                product_primitives.select().where(
                    product_primitives.c.product_id == product.id,
                    product_primitives.c.primitive_id == p.id,
                )
            ).first()
            entry = form.composition.append_entry()
            entry.primitive_id.data = f"{p.sku} — {p.name}"
            entry.quantity.data = assoc.quantity if assoc else 1
        if not product.primitives:
            form.composition.append_entry()

    form.category_id.choices = [
        (category.id, category.name) for category in get_categories()
    ]

    primitives = get_primitives()

    if form.validate_on_submit():
        try:
            update_product(product.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/product_form.html", form=form, product=product, primitives=primitives, marketplaces=marketplaces, tab=tab)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("catalog.products_list", tab=tab))

    return render_template("catalog/product_form.html", form=form, product=product, primitives=primitives, marketplaces=marketplaces, tab=tab)


@catalog_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@manager_required
def product_delete(product_id: int) -> Response:
    try:
        delete_product(product_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Товар удалён.", "success")
    return redirect(url_for("catalog.products_list"))


@catalog_bp.route("/categories")
@manager_required
def categories_list() -> str:
    get_categories()  # создаёт категорию по умолчанию при первом посещении
    q = request.args.get("q", "").strip()
    query = Category.query
    if q:
        query = query.filter(Category.name.ilike(f"%{q}%"))
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Category.id).paginate(page=page, per_page=20, error_out=False)
    return render_template("catalog/categories.html", categories=pagination.items, pagination=pagination, q=q)


@catalog_bp.route("/categories/create", methods=["GET", "POST"])
@manager_required
def category_create() -> Response | str:
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            create_category(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/category_form.html", form=form)

        flash(f"Категория {form.name.data} создана.", "success")
        return redirect(url_for("catalog.categories_list"))

    return render_template("catalog/category_form.html", form=form)


@catalog_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@manager_required
def category_edit(category_id: int) -> Response | str:
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        flash("Категория не найдена.", "error")
        return redirect(url_for("catalog.categories_list"))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        try:
            update_category(category.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/category_form.html", form=form, category=category)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("catalog.categories_list"))

    return render_template("catalog/category_form.html", form=form, category=category)


@catalog_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@manager_required
def category_delete(category_id: int) -> Response:
    try:
        delete_category(category_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Категория удалена.", "success")
    return redirect(url_for("catalog.categories_list"))


@catalog_bp.route("/marketplaces")
@admin_required
def marketplaces_list() -> str:
    page = request.args.get("page", 1, type=int)
    pagination = Marketplace.query.order_by(Marketplace.id).paginate(page=page, per_page=20, error_out=False)
    return render_template("catalog/marketplaces.html", marketplaces=pagination.items, pagination=pagination)


@catalog_bp.route("/marketplaces/create", methods=["GET", "POST"])
@admin_required
def marketplace_create() -> Response | str:
    form = MarketplaceForm()
    if form.validate_on_submit():
        try:
            create_marketplace(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/marketplace_form.html", form=form)

        flash(f"Магазин {form.name.data} создан.", "success")
        return redirect(url_for("catalog.marketplaces_list"))

    return render_template("catalog/marketplace_form.html", form=form)


@catalog_bp.route("/marketplaces/<int:marketplace_id>/edit", methods=["GET", "POST"])
@admin_required
def marketplace_edit(marketplace_id: int) -> Response | str:
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        flash("Марктеплейс не найден.", "error")
        return redirect(url_for("catalog.marketplaces_list"))

    form = MarketplaceForm(obj=marketplace)
    if form.validate_on_submit():
        try:
            update_marketplace(marketplace.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/marketplace_form.html", form=form, marketplace=marketplace)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("catalog.marketplaces_list"))

    return render_template("catalog/marketplace_form.html", form=form, marketplace=marketplace)


@catalog_bp.route("/marketplaces/<int:marketplace_id>/delete", methods=["POST"])
@admin_required
def marketplace_delete(marketplace_id: int) -> Response:
    try:
        delete_marketplace(marketplace_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Маркетплейс удален.", "success")
    return redirect(url_for("catalog.marketplaces_list"))


@catalog_bp.route("/primitives")
@manager_required
def primitives_list() -> str:
    q = request.args.get("q", "").strip()
    no_stock = request.args.get("no_stock")
    query = Primitive.query
    if q:
        query = query.filter((Primitive.name.ilike(f"%{q}%")) | (Primitive.sku.ilike(f"%{q}%")))

    page = request.args.get("page", 1, type=int)
    per_page = 20

    if no_stock == "1":
        all_items = query.order_by(Primitive.id).all()
        pagination = _paginate_items(
            [item for item in all_items if _has_no_stock(item)],
            page=page,
            per_page=per_page,
        )
    else:
        pagination = query.order_by(Primitive.id).paginate(page=page, per_page=per_page, error_out=False)
    primitives = pagination.items

    return render_template("catalog/primitives.html", primitives=primitives, pagination=pagination,
                           q=q, no_stock=no_stock)


@catalog_bp.route("/primitives/create", methods=["GET", "POST"])
@manager_required
def primitive_create() -> Response | str:
    form = PrimitiveForm()
    if form.validate_on_submit():
        try:
            create_primitive(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/primitive_form.html", form=form)
        flash(f"Примитив {form.name.data} создан.", "success")
        return redirect(url_for("catalog.primitives_list"))
    return render_template("catalog/primitive_form.html", form=form)


@catalog_bp.route("/primitives/<int:primitive_id>/edit", methods=["GET", "POST"])
@manager_required
def primitive_edit(primitive_id: int) -> Response | str:
    primitive: Primitive | None = db.session.get(Primitive, primitive_id)
    if primitive is None:
        flash("Примитив не найден.", "error")
        return redirect(url_for("catalog.primitives_list"))

    form = PrimitiveForm(obj=primitive)
    if form.validate_on_submit():
        try:
            update_primitive(primitive.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("catalog/primitive_form.html", form=form, primitive=primitive)
        flash("Изменения сохранены.", "success")
        return redirect(url_for("catalog.primitives_list"))
    return render_template("catalog/primitive_form.html", form=form, primitive=primitive)


@catalog_bp.route("/primitives/<int:primitive_id>/delete", methods=["POST"])
@manager_required
def primitive_delete(primitive_id: int) -> Response:
    try:
        delete_primitive(primitive_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Примитив удалён.", "success")
    return redirect(url_for("catalog.primitives_list"))


@catalog_bp.route("/primitives/import", methods=["POST"])
@manager_required
def primitives_import() -> Response:
    feed_url = get_setting("feed_url")
    try:
        created, updated, file_path = import_primitives_from_feed(feed_url)
        flash(f"Импорт завершён: создано {created}, обновлено {updated}. Файл: {file_path}", "success")
    except Exception as error:
        flash(f"Ошибка импорта: {error}", "error")
    return redirect(url_for("catalog.primitives_list"))
