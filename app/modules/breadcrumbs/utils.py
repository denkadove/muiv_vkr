"""Утилиты для построения хлебных крошек."""

from flask import url_for, request

SECTION_NAMES = {
    "users": "Пользователи",
    "groups": "Группы",
    "products": "Товары",
    "categories": "Категории",
    "marketplaces": "Маркетплейсы",
}

SINGULAR_NAMES = {
    "users": "пользователя",
    "groups": "группы",
    "products": "товара",
    "categories": "категории",
    "marketplaces": "маркетплейса",
}


def _get_object_name(section: str, obj_id: int) -> str:
    """Возвращает отображаемое имя объекта по разделу и id."""
    try:
        if section == "users":
            from app.modules.auth.models import User
            obj = User.query.get(obj_id)
            return obj.username if obj else f"#{obj_id}"
        if section == "groups":
            from app.modules.auth.models import UserGroup
            obj = UserGroup.query.get(obj_id)
            return obj.name if obj else f"#{obj_id}"
        if section == "products":
            from app.modules.catalog.models import Product
            obj = Product.query.get(obj_id)
            return obj.name if obj else f"#{obj_id}"
        if section == "categories":
            from app.modules.catalog.models import Category
            obj = Category.query.get(obj_id)
            return obj.name if obj else f"#{obj_id}"
        if section == "marketplaces":
            from app.modules.catalog.models import Marketplace
            obj = Marketplace.query.get(obj_id)
            return obj.name if obj else f"#{obj_id}"
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

    path = request.path.strip("/")

    if path.startswith("admin"):
        parts = path.split("/")
        # /admin/users/123/edit -> ['admin', 'users', '123', 'edit']
        if len(parts) >= 2:
            section = parts[1]
            if section in SECTION_NAMES:
                breadcrumbs.append({
                    "name": SECTION_NAMES[section],
                    "url": url_for(f"admin.{section}_list") if _endpoint_exists(f"admin.{section}_list") else None,
                })

        if len(parts) >= 3:
            action = parts[2]
            if action == "create":
                name = f"Создание {SINGULAR_NAMES.get(parts[1], 'объекта')}"
                breadcrumbs.append({"name": name, "url": None})
            elif action.isdigit():
                name = _get_object_name(parts[1], int(action))
                singular = SINGULAR_NAMES.get(parts[1], "объекта")
                # Если есть четвёртая часть (edit) — показываем «Редактирование ...: имя»
                if len(parts) >= 4 and parts[3] == "edit":
                    name = f"Редактирование {singular}: {name}"
                breadcrumbs.append({"name": name, "url": None})

    elif path.startswith("auth"):
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