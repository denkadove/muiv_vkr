from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")
    from app.main import main_bp

    app.register_blueprint(main_bp)

    from app.main.routes import register_routes

    register_routes(app)

    return app
