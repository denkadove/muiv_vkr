"""Блюпринт админ-панели."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="templates", url_prefix="/admin")

# Импорт маршрутов нужен здесь: декораторы @admin_bp.route срабатывают при импорте
from . import routes
