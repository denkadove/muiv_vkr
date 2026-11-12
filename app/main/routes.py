from flask import render_template, url_for, redirect
from flask_login import login_required
from app import db

from app.models import User, UserGroup

def register_routes(app):

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template("500.html"), 500

    @app.route("/")
    @app.route("/index")
    def index():
        usersList = User.query.all()
        return render_template("index.html", usersList=usersList)

    @app.route("/profile")
    @login_required
    def profile():
        return render_template("profile.html")