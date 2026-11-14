"""Точка входа приложения (отладочный запуск)."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Сервер разработки: для эксплуатации использовать WSGI-сервер
    app.run(debug=True)
