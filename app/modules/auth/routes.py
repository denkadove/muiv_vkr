"""Маршруты аутентификации: вход, выход, регистрация."""

from flask import Response, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import bcrypt
from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, RegisterForm
from app.modules.auth.models import User
from app.modules.auth.services import create_user


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Response | str:
    if current_user.is_authenticated:
        return redirect(url_for("profile"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.active:
                flash("Ваша учётная запись заблокирована. Обратитесь к администратору.", "error")
                return render_template("login.html", form=form)
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
    logout_user()
    session.pop("impersonator_id", None)
    session.pop("impersonated_user_id", None)
    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/registration", methods=["GET", "POST"])
def register() -> Response | str:
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