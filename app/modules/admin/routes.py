"""Маршруты админ-панели как хоста: пользователи, группы и переключение учётной записи."""

from flask import Response, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import db
from app.modules.admin import admin_bp
from app.modules.admin.forms import CreateUserForm, UserForm, UserGroupForm
from app.modules.auth.decorators import admin_required
from app.modules.auth.models import User, UserGroup
from app.modules.auth.services import (
    create_user,
    create_user_group,
    delete_user,
    delete_user_group,
    get_user_groups,
    update_user,
    update_user_group,
)
from app.modules.settings.constants import ADMIN_GROUP_ID


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
