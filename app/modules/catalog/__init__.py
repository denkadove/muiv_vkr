"""Расширение админ-панели: каталог (товары, категории, примитивы, магазины)."""

from flask import Blueprint

catalog_bp = Blueprint(
    "catalog", __name__, template_folder="templates", url_prefix="/admin"
)

from . import routes
