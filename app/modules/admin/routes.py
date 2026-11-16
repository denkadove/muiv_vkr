"""Маршруты админ-панели: управление пользователями и сущностями каталога."""

from flask import Response, flash, redirect, render_template, session, url_for, request
from flask_login import current_user, login_user, logout_user

from app.extensions import db
from app.modules.admin import admin_bp
from app.modules.admin.forms import CreateUserForm, UserForm, UserGroupForm
from app.modules.auth.decorators import admin_required
from app.modules.settings.constants import ADMIN_GROUP_ID
from app.modules.auth.models import User, UserGroup
from app.modules.catalog.forms import CategoryForm, MarketplaceForm, ProductForm
from app.modules.catalog.models import Category, Marketplace, Product
from app.modules.catalog.services import (
    create_category,
    create_marketplace,
    create_product,
    delete_category,
    delete_marketplace,
    delete_product,
    get_categories,
    update_category,
    update_marketplace,
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


@admin_bp.route("/users")
@admin_required
def users_list() -> str:
    users: list[User] = User.query.order_by(User.id).all()
    return render_template("users.html", users=users)


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
    products: list[Product] = Product.query.order_by(Product.id).all()
    return render_template("products.html", products=products)


@admin_bp.route("/products/create", methods=["GET", "POST"])
@admin_required
def product_create() -> Response | str:
    form = ProductForm()
    form.category_id.choices = [(category.id, category.name) for category in get_categories()]

    marketplaces = Marketplace.query.order_by(Marketplace.name).all()
    form.marketplaces.choices = [(mp.id, mp.name) for mp in marketplaces]

    if form.validate_on_submit():
        try:
            create_product(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("product_form.html", form=form)

        flash(f"Товар {form.name.data} создан.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("product_form.html", form=form)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id: int) -> Response | str:
    product: Product | None = db.session.get(Product, product_id)
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()

    if product is None:
        flash("Товар не найден.", "error")
        return redirect(url_for("admin.products_list"))

    form = ProductForm(obj=product)
    if request.method == "GET":
        form.marketplaces.data = [mp.id for mp in product.marketplaces]

    form.category_id.choices = [
        (category.id, category.name) for category in get_categories()
    ]

    form.marketplaces.choices = [
        (m.id, m.name) for m in Marketplace.query.all()
    ]

    if form.validate_on_submit():
        try:
            update_product(product.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("product_form.html", form=form, product=product)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.products_list"))

    return render_template("product_form.html", form=form, product=product)


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
    categories: list[Category] = Category.query.order_by(Category.id).all()
    return render_template("categories.html", categories=categories)


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
    marketplaces: list[Marketplace] = Marketplace.query.order_by(Marketplace.id).all()
    return render_template("marketplaces.html", marketplaces=marketplaces)


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


@admin_bp.route("/groups")
@admin_required
def groups_list() -> str:
    groups: list[UserGroup] = get_user_groups()
    return render_template("groups.html", groups=groups)


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