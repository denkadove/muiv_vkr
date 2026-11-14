from flask import Response, render_template, url_for, redirect
from flask_login import login_required
from app import db

from app.models import User, UserGroup

def register_routes(app):
    """Регистрирует маршруты приложения и обработчики ошибок."""

    @app.errorhandler(404)
    def page_not_found(error: Exception) -> tuple[str, int]:
        """Обработчик ошибки 404: страница не найдена.

        Аргументы:
            error: объект исключения HTTPException от Flask.

        Возвращает:
            tuple[str, int]: HTML страницы ошибки и код 404.
        """
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error: Exception) -> tuple[str, int]:
        """Обработчик ошибки 500: внутренняя ошибка сервера.

        Аргументы:
            error: объект исключения от Flask.

        Возвращает:
            tuple[str, int]: HTML страницы ошибки и код 500.
        """
        return render_template("500.html"), 500

    @app.route("/")
    def index() -> str:
        """Главная страница приложения.

        Возвращает:
            str: HTML главной страницы со списком пользователей.
        """
        usersList = User.query.all()
        return render_template("index.html", usersList=usersList)

    @app.route("/index")
    def index_alias() -> Response:
        """Старый адрес главной страницы.

        Перенаправляет на канонический адрес "/", сохраняя
        работоспособность существующих ссылок.

        Возвращает:
            Response: редирект на главную страницу.
        """
        return redirect(url_for("index"))

    @app.route("/profile")
    @login_required
    def profile() -> str:
        """Страница профиля пользователя (требует входа в систему).

        Возвращает:
            str: HTML страницы профиля.
        """
        return render_template("profile.html")