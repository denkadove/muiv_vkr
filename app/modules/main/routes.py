"""Маршруты основной части приложения."""

from flask import Flask, Response, redirect, render_template, url_for
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
        products: list[Product] = Product.query.order_by(Product.id).all()
        return render_template("index.html", products=products)

    @app.route("/index")
    def index_alias() -> Response:
        return redirect(url_for("index"))

    @app.route("/profile")
    @login_required
    def profile() -> str:
        return render_template("profile.html")