"""Маршруты основной части приложения."""

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.modules.settings.constants import ADMIN_GROUP_ID

from app.modules.catalog.models import Product


def register_routes(app: Flask) -> None:
    """Регистрирует маршруты и обработчики ошибок основной части."""

    @app.errorhandler(404)
    def page_not_found(error: Exception) -> tuple[str, int]:
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error: Exception) -> tuple[str, int]:
        return render_template("500.html"), 500

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/about")
    def about() -> str:
        return render_template("about.html")

    @app.route("/products")
    def products_public() -> str:
        page = request.args.get("page", 1, type=int)
        pagination = Product.query.order_by(Product.id).paginate(page=page, per_page=20, error_out=False)
        return render_template("products.html", products=pagination.items, pagination=pagination)

    @app.route("/profile")
    @login_required
    def profile() -> str:
        return redirect(url_for("profile_view", user_id=current_user.id))

    @app.route("/profile/<int:user_id>")
    @login_required
    def profile_view(user_id: int) -> str:
        from app.modules.auth.models import User

        user = db.session.get(User, user_id)
        if user is None:
            flash("Пользователь не найден.", "error")
            return redirect(url_for("index"))
        can_edit = (user_id == current_user.id) or (current_user.group_id == ADMIN_GROUP_ID)
        return render_template("profile_view.html", user=user, can_edit=can_edit)

    @app.route("/profile/<int:user_id>/edit", methods=["GET", "POST"])
    @login_required
    def profile_edit(user_id: int) -> str:
        from app.modules.auth.forms import ProfileForm
        from app.modules.auth.models import User
        from werkzeug.utils import secure_filename
        import os

        user = db.session.get(User, user_id)
        if user is None:
            flash("Пользователь не найден.", "error")
            return redirect(url_for("index"))

        is_admin = current_user.group_id == ADMIN_GROUP_ID
        is_self = user_id == current_user.id
        if not (is_self or is_admin):
            flash("Недостаточно прав.", "error")
            return redirect(url_for("profile_view", user_id=user_id))

        form = ProfileForm()
        if request.method == "GET":
            form.name.data = user.name
            form.phone.data = user.phone
            form.position.data = user.position
            form.department.data = user.department
            form.email.data = user.email
            form.group_id.data = user.group_id

        if form.validate_on_submit():
            user.name = form.name.data.strip() if form.name.data else None
            user.phone = form.phone.data.strip() if form.phone.data else None
            user.position = form.position.data.strip() if form.position.data else None
            user.department = form.department.data.strip() if form.department.data else None

            if is_admin:
                if form.email.data:
                    user.email = form.email.data.strip()
                if form.group_id.data:
                    user.group_id = form.group_id.data

            if form.password.data:
                from app.modules.auth.services import _hash_password
                user.password = _hash_password(form.password.data)

            avatar = request.files.get("avatar")
            if avatar and avatar.filename:
                if avatar.content_length and avatar.content_length > 1 * 1024 * 1024:
                    flash("Файл аватара слишком большой (макс. 1 МБ).", "error")
                    return render_template("profile_edit.html", form=form, user=user, is_admin=is_admin)
                ext = os.path.splitext(avatar.filename)[1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                    flash("Недопустимый формат аватара.", "error")
                    return render_template("profile_edit.html", form=form, user=user, is_admin=is_admin)
                filename = secure_filename(f"avatar_{user.id}{ext}")
                upload_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "static", "uploads", "avatars"
                )
                os.makedirs(upload_dir, exist_ok=True)
                avatar.save(os.path.join(upload_dir, filename))
                user.avatar = filename

            db.session.commit()
            flash("Профиль обновлён.", "success")
            return redirect(url_for("profile_view", user_id=user_id))

        return render_template("profile_edit.html", form=form, user=user, is_admin=is_admin)