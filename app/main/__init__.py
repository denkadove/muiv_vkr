"""Блюпринт основной части приложения."""

from flask import Blueprint

main_bp = Blueprint("main", __name__, template_folder="templates")
