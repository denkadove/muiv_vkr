"""Утилиты для построения хлебных крошек."""

import importlib

from flask import request, url_for

from app.extensions import db
from app.registry import get_breadcrumb_sections


def _get_object_name(section: str, obj_id: int) -> str:
    """Возвращает отображаемое имя объекта по описанию раздела и id."""
    meta = get_breadcrumb_sections().get(section)
    if meta is not None and meta.model is not None:
        try:
            module_path, class_name = meta.model.rsplit(".", 1)
            model = getattr(importlib.import_module(module_path), class_name)
            obj = db.session.get(model, obj_id)
            if obj is not None:
                return getattr(obj, meta.name_field) or f"#{obj_id}"
        except Exception:
            pass
    return f"#{obj_id}"


def _endpoint_exists(endpoint: str) -> bool:
    try:
        url_for(endpoint)
        return True
    except Exception:
        return False


def build_breadcrumbs():
    """Формирует список хлебных крошек на основе текущего URL."""
    breadcrumbs = [{"name": "Главная", "url": url_for("index")}]
    sections = get_breadcrumb_sections()

    path = request.path.strip("/")

    parts = path.split("/") if path else []
    # /admin/users/123/edit -> ['admin', 'users', '123', 'edit']
    # расширение с собственным префиксом -> ['reports', '123', 'edit']
    offset = 1 if parts and parts[0] == "admin" else 0
    meta = sections.get(parts[offset]) if len(parts) > offset else None

    if meta is not None:
        breadcrumbs.append({
            "name": meta.name,
            "url": url_for(meta.endpoint) if _endpoint_exists(meta.endpoint) else None,
        })

        if len(parts) > offset + 1:
            action = parts[offset + 1]
            if action == "create":
                breadcrumbs.append({"name": f"Создание {meta.singular}", "url": None})
            elif action.isdigit():
                name = _get_object_name(parts[offset], int(action))
                # '/admin/products/1/edit' -> показываем «Редактирование ...: имя»
                if len(parts) > offset + 2 and parts[offset + 2] == "edit":
                    name = f"Редактирование {meta.singular}: {name}"
                breadcrumbs.append({"name": name, "url": None})

    if path.startswith("auth"):
        parts = path.split("/")
        if len(parts) >= 2:
            action = parts[1]
            names = {
                "login": "Вход",
                "registration": "Регистрация",
                "logout": "Выход",
            }
            if action in names:
                breadcrumbs.append({"name": names[action], "url": None})

    return breadcrumbs
