"""Маршруты основной части приложения."""

from flask import Flask, Response, render_template, url_for, redirect
from flask_login import login_required

from app.models import User


def register_routes(app: Flask) -> None:
    """Регистрирует маршруты и обработчики ошибок основной части.

    Аргументы:
        app (Flask): экземпляр приложения.

    Возвращает:
        None
    """
    @app.errorhandler(404)
    def page_not_found(error: Exception) -> tuple[str, int]:
        """Отдаёт страницу 404.

        Аргументы:
            error (Exception): исключение, вызвавшее ошибку.

        Возвращает:
            tuple[str, int]: HTML страницы и код 404.
        """
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error: Exception) -> tuple[str, int]:
        """Отдаёт страницу 500.

        Аргументы:
            error (Exception): исключение, вызвавшее ошибку.

        Возвращает:
            tuple[str, int]: HTML страницы и код 500.
        """
        return render_template("500.html"), 500

    @app.route("/")
    def index() -> str:
        """Главная страница: список зарегистрированных пользователей.

        Возвращает:
            str: HTML главной страницы.
        """
        users_list: list[User] = User.query.all()
        return render_template("index.html", users_list=users_list)

    @app.route("/index")
    def index_alias() -> Response:
        """Перенаправляет /index на канонический адрес "/" (совместимость ссылок).

        Возвращает:
            Response: редирект на главную страницу.
        """
        return redirect(url_for("index"))

    @app.route("/profile")
    @login_required
    def profile() -> str:
        """Страница профиля пользователя (только после входа).

        Возвращает:
            str: HTML страницы профиля.
        """
        return render_template("profile.html")
