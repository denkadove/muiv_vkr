from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy 

bcrypt = Bcrypt()
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    bcrypt.init_app(app)
    db.init_app(app)

    from app.main import main_bp
    from app.auth import auth_bp

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    migrate = Migrate(app, db)

    from app.models import User

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.main.routes import register_routes

    register_routes(app)

    return app
