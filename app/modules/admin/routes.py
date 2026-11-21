"""Маршруты админ-панели: управление пользователями и сущностями каталога."""

from flask import Response, flash, redirect, render_template, session, url_for, request
from flask_login import current_user, login_user, logout_user
from flask_sqlalchemy.pagination import Pagination

from app.extensions import db
from app.modules.admin import admin_bp
from app.modules.admin.forms import CreateUserForm, UserForm, UserGroupForm
from app.modules.auth.decorators import admin_required
from app.modules.settings.constants import ADMIN_GROUP_ID
from app.modules.settings.services import get_setting
from app.modules.auth.models import User, UserGroup
from app.modules.catalog.forms import CategoryForm, MarketplaceForm, PrimitiveForm, ProductForm
from app.modules.catalog.models import Category, Marketplace, Primitive, Product, ProductMarketplace, product_primitives
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
from app.modules.auth.services import (
    create_user,
    create_user_group,
    delete_user,
    delete_user_group,
    get_user_groups,
    update_user,
    update_user_group,
)

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
    for marketplace in marketplaces:
        entry = form.marketplace_statuses.append_entry()
        entry.marketplace_id.data = marketplace.id
        entry.status.data = (
            product.marketplace_status(marketplace.id) if product else None
        ) or "x"


@admin_bp.route("/users")
@admin_required
def users_list() -> str:
    q = request.args.get("q", "").strip()
    group_id = request.args.get("group_id", type=int)
    active = request.args.get("active")

    query = User.query
    if q:
        query = query.filter((User.username.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
    if group_id:
        query = query.filter(User.group_id == group_id)
    if active == "1":
        query = query.filter(User.active.is_(True))

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(User.id).paginate(page=page, per_page=20, error_out=False)
    groups = get_user_groups()
    return render_template("users.html", users=pagination.items, pagination=pagination, groups=groups,
                           q=q, group_id=group_id, active=active)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def user_create() -> Response | str:
    form = CreateUserForm()
    form.group_id.choices = [(g.id, g.name) for g in get_user_groups()]
    if form.validate_on_submit():
        try:
            create_user(form, group_id=form.group_id.data, active=form.active.data)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("user_form.html", form=form)

        flash(f"Пользователь {form.username.data} создан.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("user_form.html", form=form)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id: int) -> Response | str:
    user: User | None = db.session.get(User, user_id)
    if user is None:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("admin.users_list"))

    form = UserForm(obj=user)
    form.group_id.choices = [(g.id, g.name) for g in get_user_groups()]
    if form.validate_on_submit():
        try:
            update_user(user.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("user_form.html", form=form, user=user)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("user_form.html", form=form, user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id: int) -> Response:
    try:
        delete_user(user_id, current_user.id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Пользователь удалён.", "success")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/<int:user_id>/impersonate", methods=["POST"])
@admin_required
def user_impersonate(user_id: int) -> Response:
    if user_id == current_user.id:
        flash("Вы уже работаете от своего имени.", "error")
        return redirect(url_for("admin.users_list"))

    target: User | None = db.session.get(User, user_id)
    if target is None:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("admin.users_list"))

    if not target.active:
        flash("Нельзя переключиться на заблокированную учётную запись.", "error")
        return redirect(url_for("admin.users_list"))

    if target.group_id == ADMIN_GROUP_ID:
        flash("Нельзя переключиться на администратора.", "error")
        return redirect(url_for("admin.users_list"))

    session["impersonator_id"] = current_user.id
    session["impersonated_user_id"] = target.id
    login_user(target, remember=False)
    flash(f"Вы работаете от имени {target.username}.", "warning")
    return redirect(url_for("index"))


@admin_bp.route("/impersonate/stop", methods=["POST"])
def impersonate_stop() -> Response:
    impersonator_id: int | None = session.get("impersonator_id")
    if impersonator_id is None:
        flash("Режим переключения не активен.", "error")
        return redirect(url_for("index"))

    impersonated_id: int | None = session.pop("impersonated_user_id", None)
    session.pop("impersonator_id", None)

    if not current_user.is_authenticated or current_user.id != impersonated_id:
        logout_user()
        flash("Сессия завершена: войдите заново.", "error")
        return redirect(url_for("auth.login"))

    impersonator: User | None = db.session.get(User, int(impersonator_id))
    if (
        impersonator is None
        or not impersonator.active
        or impersonator.group_id != ADMIN_GROUP_ID
    ):
        logout_user()
        flash("Сессия администратора недоступна: войдите заново.", "error")
        return redirect(url_for("auth.login"))

    login_user(impersonator, remember=False)
    flash(f"Вы вернулись к учётной записи {impersonator.username}.", "success")
    return redirect(url_for("index"))


@admin_bp.route("/products")
@admin_required
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
    return render_template("products.html", products=products, pagination=pagination,
                           categories=categories, marketplaces=marketplaces,
                           q=q, category_id=category_id, marketplace_id=marketplace_id,
                           marketplace_status=marketplace_status, no_stock=no_stock, active=active,
                           tab=tab)


@admin_bp.route("/products/create", methods=["GET", "POST"])
@admin_required
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
            return render_template("product_form.html", form=form, primitives=primitives, marketplaces=marketplaces, tab=tab)

        flash(f"Товар {form.name.data} создан.", "success")
        return redirect(url_for("admin.products_list", tab=tab))

    return render_template("product_form.html", form=form, primitives=primitives, marketplaces=marketplaces, tab=tab)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id: int) -> Response | str:
    tab = request.args.get("tab", "main")
    product: Product | None = db.session.get(Product, product_id)
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()

    if product is None:
        flash("Товар не найден.", "error")
        return redirect(url_for("admin.products_list"))

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
            return render_template("product_form.html", form=form, product=product, primitives=primitives, marketplaces=marketplaces, tab=tab)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.products_list", tab=tab))

    return render_template("product_form.html", form=form, product=product, primitives=primitives, marketplaces=marketplaces, tab=tab)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id: int) -> Response:
    try:
        delete_product(product_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Товар удалён.", "success")
    return redirect(url_for("admin.products_list"))


@admin_bp.route("/categories")
@admin_required
def categories_list() -> str:
    get_categories()  # создаёт категорию по умолчанию при первом посещении
    q = request.args.get("q", "").strip()
    query = Category.query
    if q:
        query = query.filter(Category.name.ilike(f"%{q}%"))
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Category.id).paginate(page=page, per_page=20, error_out=False)
    return render_template("categories.html", categories=pagination.items, pagination=pagination, q=q)


@admin_bp.route("/categories/create", methods=["GET", "POST"])
@admin_required
def category_create() -> Response | str:
    form = CategoryForm()
    if form.validate_on_submit():
        try:
            create_category(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("category_form.html", form=form)

        flash(f"Категория {form.name.data} создана.", "success")
        return redirect(url_for("admin.categories_list"))

    return render_template("category_form.html", form=form)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def category_edit(category_id: int) -> Response | str:
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        flash("Категория не найдена.", "error")
        return redirect(url_for("admin.categories_list"))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        try:
            update_category(category.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("category_form.html", form=form, category=category)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.categories_list"))

    return render_template("category_form.html", form=form, category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def category_delete(category_id: int) -> Response:
    try:
        delete_category(category_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Категория удалена.", "success")
    return redirect(url_for("admin.categories_list"))


@admin_bp.route("/marketplaces")
@admin_required
def marketplaces_list() -> str:
    page = request.args.get("page", 1, type=int)
    pagination = Marketplace.query.order_by(Marketplace.id).paginate(page=page, per_page=20, error_out=False)
    return render_template("marketplaces.html", marketplaces=pagination.items, pagination=pagination)


@admin_bp.route("/marketplaces/create", methods=["GET", "POST"])
@admin_required
def marketplace_create() -> Response | str:
    form = MarketplaceForm()
    if form.validate_on_submit():
        try:
            create_marketplace(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("marketplace_form.html", form=form)

        flash(f"Магазин {form.name.data} создан.", "success")
        return redirect(url_for("admin.marketplaces_list"))

    return render_template("marketplace_form.html", form=form)


@admin_bp.route("/marketplaces/<int:marketplace_id>/edit", methods=["GET", "POST"])
@admin_required
def marketplace_edit(marketplace_id: int) -> Response | str:
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        flash("Марктеплейс не найден.", "error")
        return redirect(url_for("admin.marketplaces_list"))

    form = MarketplaceForm(obj=marketplace)
    if form.validate_on_submit():
        try:
            update_marketplace(marketplace.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("marketplace_form.html", form=form, marketplace=marketplace)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.marketplaces_list"))

    return render_template("marketplace_form.html", form=form, marketplace=marketplace)


@admin_bp.route("/marketplaces/<int:marketplace_id>/delete", methods=["POST"])
@admin_required
def marketplace_delete(marketplace_id: int) -> Response:
    try:
        delete_marketplace(marketplace_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Маркетплейс удален.", "success")
    return redirect(url_for("admin.marketplaces_list"))


@admin_bp.route("/primitives")
@admin_required
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

    return render_template("primitives.html", primitives=primitives, pagination=pagination,
                           q=q, no_stock=no_stock)


@admin_bp.route("/primitives/create", methods=["GET", "POST"])
@admin_required
def primitive_create() -> Response | str:
    form = PrimitiveForm()
    if form.validate_on_submit():
        try:
            create_primitive(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("primitive_form.html", form=form)
        flash(f"Примитив {form.name.data} создан.", "success")
        return redirect(url_for("admin.primitives_list"))
    return render_template("primitive_form.html", form=form)


@admin_bp.route("/primitives/<int:primitive_id>/edit", methods=["GET", "POST"])
@admin_required
def primitive_edit(primitive_id: int) -> Response | str:
    primitive: Primitive | None = db.session.get(Primitive, primitive_id)
    if primitive is None:
        flash("Примитив не найден.", "error")
        return redirect(url_for("admin.primitives_list"))

    form = PrimitiveForm(obj=primitive)
    if form.validate_on_submit():
        try:
            update_primitive(primitive.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("primitive_form.html", form=form, primitive=primitive)
        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.primitives_list"))
    return render_template("primitive_form.html", form=form, primitive=primitive)


@admin_bp.route("/primitives/<int:primitive_id>/delete", methods=["POST"])
@admin_required
def primitive_delete(primitive_id: int) -> Response:
    try:
        delete_primitive(primitive_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Примитив удалён.", "success")
    return redirect(url_for("admin.primitives_list"))


@admin_bp.route("/primitives/import", methods=["POST"])
@admin_required
def primitives_import() -> Response:
    feed_url = get_setting("feed_url")
    try:
        created, updated, file_path = import_primitives_from_feed(feed_url)
        flash(f"Импорт завершён: создано {created}, обновлено {updated}. Файл: {file_path}", "success")
    except Exception as error:
        flash(f"Ошибка импорта: {error}", "error")
    return redirect(url_for("admin.primitives_list"))


@admin_bp.route("/groups")
@admin_required
def groups_list() -> str:
    get_user_groups()  # создаёт группы по умолчанию при первом посещении
    q = request.args.get("q", "").strip()
    active = request.args.get("active")

    query = UserGroup.query
    if q:
        query = query.filter(UserGroup.name.ilike(f"%{q}%"))
    if active == "1":
        query = query.filter(UserGroup.active.is_(True))

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(UserGroup.id).paginate(page=page, per_page=20, error_out=False)
    groups = pagination.items
    # кол-во пользователей в группе
    user_counts = {g.id: User.query.filter_by(group_id=g.id).count() for g in groups}
    return render_template("groups.html", groups=groups, pagination=pagination,
                           user_counts=user_counts, q=q, active=active)


@admin_bp.route("/groups/create", methods=["GET", "POST"])
@admin_required
def group_create() -> Response | str:
    form = UserGroupForm()
    if form.validate_on_submit():
        try:
            create_user_group(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("group_form.html", form=form)
        flash(f"Группа {form.name.data} создана.", "success")
        return redirect(url_for("admin.groups_list"))
    return render_template("group_form.html", form=form)


@admin_bp.route("/groups/<int:group_id>/edit", methods=["GET", "POST"])
@admin_required
def group_edit(group_id: int) -> Response | str:
    group: UserGroup | None = db.session.get(UserGroup, group_id)
    if group is None:
        flash("Группа не найдена.", "error")
        return redirect(url_for("admin.groups_list"))

    form = UserGroupForm(obj=group)
    if form.validate_on_submit():
        try:
            update_user_group(group.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("group_form.html", form=form, group=group)
        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.groups_list"))
    return render_template("group_form.html", form=form, group=group)


@admin_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@admin_required
def group_delete(group_id: int) -> Response:
    try:
        delete_user_group(group_id)
    except (ValueError, LookupError) as error:
        flash(str(error), "error")
    else:
        flash("Группа удалена.", "success")
    return redirect(url_for("admin.groups_list"))