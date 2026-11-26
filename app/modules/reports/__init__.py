"""Блюпринт отчётов: генерация и скачивание xlsx-файлов."""

from flask import Blueprint

reports_bp = Blueprint(
    "reports", __name__, template_folder="templates", url_prefix="/admin/reports"
)

from app.modules.reports import routes  # noqa: E402, F401