"""Маршруты аутентификации: вход, выход, регистрация."""

from flask import Response, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app import bcrypt
from app.auth import auth_bp
from app.forms import LoginForm, RegisterForm
from app.models import User
from app.services import create_user


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Response | str:
    """Вход в систему.

    Особенности:
        - заблокированному аккаунту вход запрещён;
        - сессия при входе очищается от ключей режима переключения
          (иначе вход дал бы права администратора).

    Возвращает:
        Response | str: HTML формы входа или редирект.
    """
    if current_user.is_authenticated:
        return redirect(url_for("profile"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.active:
                flash("Ваша учётная запись заблокирована. Обратитесь к администратору.", "error")
                return render_template("login.html", form=form)
            # Новая сессия не должна наследовать режим переключения,
            # иначе вход под своим паролём мог бы дать права администратора
            session.pop("impersonator_id", None)
            session.pop("impersonated_user_id", None)
            login_user(user)
            flash(f"Добро пожаловать, {user.username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль.", "error")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
def logout() -> Response:
    """Выход из системы; очищает ключи режима переключения.

    Возвращает:
        Response: редирект на главную страницу.
    """
    logout_user()
    session.pop("impersonator_id", None)
    session.pop("impersonated_user_id", None)
    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/registration", methods=["GET", "POST"])
def register() -> Response | str:
    """Регистрация нового пользователя; ошибки уникальности — через flash.

    Возвращает:
        Response | str: HTML формы регистрации или редирект на вход.
    """
    form = RegisterForm()

    if form.validate_on_submit():
        try:
            create_user(form)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("register.html", form=form)

        flash(
            "Регистрация прошла успешно! Теперь вы можете войти в систему.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)
