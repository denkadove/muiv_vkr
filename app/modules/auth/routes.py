"""Маршруты аутентификации: вход, выход, регистрация."""

from datetime import datetime, timezone

from flask import Response, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import bcrypt, db, mail
from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, RegisterForm
from app.modules.auth.models import PasswordResetToken, User
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
            login_user(user, remember=form.remember_me.data)
            user.last_visit = datetime.now(timezone.utc)
            db.session.commit()
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

        flash("Регистрация прошла успешно! Теперь вы можете войти в систему.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Response | str:
    """Запрос на восстановление пароля."""
    from flask import request
    from flask_mail import Message

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = User.query.filter_by(email=email).first()
        if user:
            import secrets

            token = secrets.token_urlsafe(32)
            reset = PasswordResetToken(user_id=user.id, token=token)
            db.session.add(reset)
            db.session.commit()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            msg = Message(
                subject="Восстановление пароля",
                recipients=[email],
                body=f"Для сброса пароля перейдите по ссылке: {reset_url}",
            )
            mail.send(msg)
        flash("Если email зарегистрирован, ссылка для сброса пароля отправлена.", "success")
        return redirect(url_for("auth.login"))

    return render_template("forgot_password.html")


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str) -> Response | str:
    """Сброс пароля по токену."""
    from datetime import timedelta

    from flask import request

    reset = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if reset is None or (datetime.now(timezone.utc) - reset.created_at).total_seconds() > 3600:
        flash("Ссылка недействительна или истекла.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 6:
            flash("Пароль должен быть не менее 6 символов.", "error")
            return render_template("reset_password.html", token=token)
        if password != confirm:
            flash("Пароли не совпадают.", "error")
            return render_template("reset_password.html", token=token)

        from app.modules.auth.services import _hash_password

        reset.user.password = _hash_password(password)
        reset.used = True
        db.session.commit()
        flash("Пароль изменён. Войдите с новым паролем.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)