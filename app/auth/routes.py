from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user

from app import bcrypt, db
from app.auth import auth_bp
from app.forms import LoginForm, RegisterForm
from app.models import User, UserGroup

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("profile"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.active:
                flash("Ваша учётная запись заблокирована. Обратитесь к администратору.", "error")
                return render_template("login.html", form=form)
            login_user(user)
            flash(f"Добро пожаловать, {user.username}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Неверный логин или пароль.", "error")

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Вы успешно вышли из системы.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/registration", methods=["GET", "POST"])
def register():

    form = RegisterForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()

        if existing_user:
            flash("Пользователь с таким логином уже существует.", "error")
            return render_template("register.html", form=form)

        if existing_email:
            flash("Пользователь с таким email уже существует.", "error")
            return render_template("register.html", form=form)

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            "utf-8"
        )

        user = User(
            username=form.username.data,
            email=form.email.data,
            password=hashed_password,
            group_id=2,
        )

        userList = User.query.all()

        if userList == []:
            user.group_id=1

        db.session.add(user)
        db.session.commit()

        flash(
            "Регистрация прошла успешно! Теперь вы можете войти в систему.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)