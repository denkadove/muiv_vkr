from flask import render_template, url_for, redirect


def register_routes(app):

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html"), 404

    @app.route("/")
    @app.route("/index")
    def index():
        return render_template("index.html")
