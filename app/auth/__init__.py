"""Блюпринт аутентификации."""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__,
                     template_folder='templates',
                     url_prefix='/auth')

# Импорт маршрутов нужен здесь: декораторы @auth_bp.route срабатывают при импорте
from . import routes
