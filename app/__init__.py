"""Фабрика приложения: инициализация расширений и блюпринтов."""

import importlib
import os

from flask import Flask, session

from app.extensions import bcrypt, csrf, db, login_manager, mail, migrate
from app.registry import ADMIN_EXTENSIONS, get_admin_menu

# Общие экземпляры расширений, привязываются к приложению в create_app


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
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from app.modules.auth import auth_bp
    from app.modules.feedback import feedback_bp
    from app.modules.main import main_bp

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы получить доступ к этой странице."
    login_manager.login_message_category = "error"

    from app.modules.settings.constants import ADMIN_GROUP_ID, MANAGER_GROUP_ID
    from app.modules.auth.models import User

    app.register_blueprint(auth_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(main_bp)

    # Админка — хост: подключает расширения и их модели по реестру.
    for extension in ADMIN_EXTENSIONS:
        for model_module in extension.models:
            importlib.import_module(model_module)
        app.register_blueprint(extension.blueprint)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_admin_group_id() -> dict[str, int]:
        return {
            "ADMIN_GROUP_ID": ADMIN_GROUP_ID,
            "MANAGER_GROUP_ID": MANAGER_GROUP_ID,
        }

    @app.context_processor
    def inject_user_role() -> dict:
        from flask_login import current_user

        is_admin = False
        is_manager = False
        if current_user.is_authenticated:
            is_admin = current_user.group_id == ADMIN_GROUP_ID
            is_manager = current_user.group_id == MANAGER_GROUP_ID
        return {"is_admin": is_admin, "is_manager": is_manager}

    @app.context_processor
    def inject_admin_menu() -> dict:
        return {"admin_menu": get_admin_menu()}

    @app.context_processor
    def inject_impersonator() -> dict[str, User | None]:
        impersonator_id: int | None = session.get("impersonator_id")
        if impersonator_id is None:
            return {"impersonator": None}
        return {"impersonator": db.session.get(User, int(impersonator_id))}

    from app.modules.main.routes import register_routes

    register_routes(app)

    from app.modules.breadcrumbs.utils import build_breadcrumbs
    from app.modules.catalog.pricing import get_exchange_rate, rub_to_usd, usd_to_rub
    from app.modules.settings.services import get_setting

    @app.context_processor
    def inject_breadcrumbs() -> dict:
        return {"breadcrumbs": build_breadcrumbs()}

    @app.context_processor
    def inject_tiny_api_key() -> dict:
        key = get_setting("tiny_api_key") or os.environ.get("TINY_API_KEY") or "no-api-key"
        return {"tiny_api_key": key}

    @app.context_processor
    def inject_exchange_rate() -> dict:
        return {
            "exchange_rate": get_exchange_rate(),
            "usd_to_rub": usd_to_rub,
            "rub_to_usd": rub_to_usd,
        }

    return app