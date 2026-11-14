"""Фабрика приложения: инициализация расширений и блюпринтов."""

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Общие экземпляры расширений, привязываются к приложению в create_app
bcrypt = Bcrypt()
db = SQLAlchemy()
login_manager = LoginManager()


def create_app() -> Flask:
    """Создаёт и настраивает экземпляр Flask-приложения.

    Возвращает:
        Flask: настроенное приложение.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    bcrypt.init_app(app)
    db.init_app(app)

    from app.main import main_bp
    from app.auth import auth_bp

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    Migrate(app, db)

    from app.models import User

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Загружает пользователя по id для flask-login.

        Аргументы:
            user_id (str): идентификатор пользователя из сессии.

        Возвращает:
            User | None: пользователь или None, если не найден.
        """
        return db.session.get(User, int(user_id))

    from app.main.routes import register_routes

    register_routes(app)

    return app
