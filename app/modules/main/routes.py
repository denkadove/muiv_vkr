"""Маршруты основной части приложения."""

from flask import Flask, render_template, request
from flask_login import login_required

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
        return render_template("profile.html")