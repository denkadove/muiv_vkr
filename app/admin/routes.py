"""Маршруты админ-панели: управление пользователями и переключение на них."""

from flask import Response, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.admin import admin_bp
from app.auth.decorators import admin_required
from app.forms import CreateUserForm, UserEditForm
from app.models import ADMIN_GROUP_ID, User
from app.services import admin_create_user, admin_update_user, delete_user


@admin_bp.route("/users")
@admin_required
def users_list() -> str:
    """Список всех пользователей системы.

    Возвращает:
        str: HTML страницы со списком пользователей.
    """
    users: list[User] = User.query.order_by(User.id).all()
    return render_template("users.html", users=users)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def user_create() -> Response | str:
    """Создание пользователя администратором.

    Особенности:
        - создание выполняет сервис admin_create_user;
        - ошибки уникальности логина/email показываются через flash.

    Возвращает:
        Response | str: HTML формы создания или редирект на список.
    """
    form = CreateUserForm()
    if form.validate_on_submit():
        try:
            admin_create_user(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("user_create.html", form=form)

        flash(f"Пользователь {form.username.data} создан.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("user_create.html", form=form)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def user_edit(user_id: int) -> Response | str:
    """Редактирование пользователя (без смены пароля).

    Особенности:
        - форма предзаполняется данными пользователя;
        - правку выполняет сервис admin_update_user, ошибки — через flash.

    Аргументы:
        user_id (int): идентификатор пользователя.

    Возвращает:
        Response | str: HTML формы правки или редирект на список.
    """
    user: User | None = db.session.get(User, user_id)
    if user is None:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("admin.users_list"))

    form = UserEditForm(obj=user)
    if form.validate_on_submit():
        try:
            admin_update_user(user.id, form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("user_edit.html", form=form, user=user)

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("user_edit.html", form=form, user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id: int) -> Response:
    """Удаление пользователя (только POST, подтверждение в браузере).

    Особенности:
        - удаление выполняет сервис delete_user, ошибки — через flash.

    Аргументы:
        user_id (int): идентификатор удаляемого пользователя.

    Возвращает:
        Response: редирект на список пользователей.
    """
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
    """Переключает сессию администратора на указанного пользователя.

    Особенности:
        - идентификаторы администратора и цели сохраняются в сессии;
        - запрещено переключение на себя, заблокированных и администраторов.

    Аргументы:
        user_id (int): идентификатор пользователя, под которым войти.

    Возвращает:
        Response: редирект на главную страницу или список.

    Исключения:
        не вызывает.
    """
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
    """Возвращает администратора из режима работы от имени пользователя.

    Особенности:
        - без admin_required: текущий пользователь — цель переключения;
        - права возвращаются только при совпадении текущего пользователя
          с целью и при живом активном администраторе; иначе сессия
          завершается полностью.

    Аргументы:
        нет.

    Возвращает:
        Response: редирект на главную страницу или страницу входа.

    Исключения:
        не вызывает.
    """
    impersonator_id: int | None = session.get("impersonator_id")
    if impersonator_id is None:
        flash("Режим переключения не активен.", "error")
        return redirect(url_for("index"))

    impersonated_id: int | None = session.pop("impersonated_user_id", None)
    session.pop("impersonator_id", None)

    if not current_user.is_authenticated or current_user.id != impersonated_id:
        # Состояние не соответствует активному режиму: права не выдаются
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
