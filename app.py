"""Точка входа приложения (отладочный запуск)."""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Сервер разработки: для эксплуатации использовать WSGI-сервер
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug)
