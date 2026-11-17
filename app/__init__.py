"""Фабрика приложения: инициализация расширений и блюпринтов."""

from flask import Flask, session

from app.extensions import bcrypt, csrf, db, login_manager, migrate

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
    migrate.init_app(app, db)

    from app.modules.admin import admin_bp
    from app.modules.auth import auth_bp
    from app.modules.catalog import catalog_bp
    from app.modules.main import main_bp
    from app.modules.settings import settings_bp

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы получить доступ к этой странице."
    login_manager.login_message_category = "error"

    from app.modules.settings.constants import ADMIN_GROUP_ID
    from app.modules.auth.models import User
    # Импорт моделей каталога для регистрации в SQLAlchemy
    from app.modules.catalog import models as catalog_models  # noqa: F401
    from app.modules.settings import models as settings_models  # noqa: F401

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(settings_bp)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_admin_group_id() -> dict[str, int]:
        return {"ADMIN_GROUP_ID": ADMIN_GROUP_ID}

    @app.context_processor
    def inject_impersonator() -> dict[str, User | None]:
        impersonator_id: int | None = session.get("impersonator_id")
        if impersonator_id is None:
            return {"impersonator": None}
        return {"impersonator": db.session.get(User, int(impersonator_id))}

    from app.modules.main.routes import register_routes

    register_routes(app)

    from app.modules.breadcrumbs.utils import build_breadcrumbs

    @app.context_processor
    def inject_breadcrumbs() -> dict:
        return {"breadcrumbs": build_breadcrumbs()}

    return app