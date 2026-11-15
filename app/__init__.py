"""Фабрика приложения: инициализация расширений и блюпринтов."""
# import os
from flask import Flask, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
# from cryptography.fernet import Fernet

# Общие экземпляры расширений, привязываются к приложению в create_app
bcrypt = Bcrypt()
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
# Инициализируем шифратор ключом из .env
# cipher = Fernet(os.environ["ENCRYPTION_KEY"].encode())

def create_app() -> Flask:
    """Создаёт и настраивает экземпляр Flask-приложения.

    Возвращает:
        Flask: настроенное приложение.
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")

    bcrypt.init_app(app)
    db.init_app(app)
    csrf.init_app(app)

    from app.main import main_bp
    from app.auth import auth_bp
    from app.admin import admin_bp

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    Migrate(app, db)

    from app.models import ADMIN_GROUP_ID, User


    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        """Загружает пользователя по id для flask-login.

        Аргументы:
            user_id (str): идентификатор пользователя из сессии.

        Возвращает:
            User | None: пользователь или None, если не найден.
        """
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_admin_group_id() -> dict[str, int]:
        """Передаёт в шаблоны константу группы администраторов.

        Возвращает:
            dict[str, int]: словарь с константой ADMIN_GROUP_ID.
        """
        return {"ADMIN_GROUP_ID": ADMIN_GROUP_ID}

    @app.context_processor
    def inject_impersonator() -> dict[str, User | None]:
        """Передаёт в шаблоны администратора в режиме переключения.

        Особенности:
            - запрос к базе выполняется только в режиме переключения.

        Возвращает:
            dict[str, User | None]: словарь с impersonator или None.
        """
        impersonator_id: int | None = session.get("impersonator_id")
        if impersonator_id is None:
            return {"impersonator": None}
        return {"impersonator": db.session.get(User, int(impersonator_id))}

    from app.main.routes import register_routes

    register_routes(app)

    return app
