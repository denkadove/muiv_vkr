"""Реестр расширений админ-панели.

Расширение — это блюпринт со своим UI, пунктами меню и метаданными для
breadcrumbs. Админка выступает хостом: она собирает меню и крошки из этого
реестра, а не знает о каждом разделе вручную.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from flask import Blueprint


@dataclass(frozen=True)
class MenuItem:
    """Пункт меню админ-панели."""

    title: str
    endpoint: str
    active_endpoints: tuple[str, ...] = ()


@dataclass(frozen=True)
class MenuSection:
    """Группа пунктов меню."""

    title: str
    items: tuple[MenuItem, ...]


@dataclass(frozen=True)
class BreadcrumbSection:
    """Описание раздела для хлебных крошек."""

    name: str
    singular: str
    endpoint: str
    model: str | None = None
    name_field: str = "name"


@dataclass(frozen=True)
class AdminExtension:
    """Расширение админ-панели."""

    key: str
    title: str
    blueprint_path: str  # "путь.к.модулю:имя_блюпринта", импорт отложенный
    menu: tuple[MenuSection, ...] = ()
    breadcrumbs: dict[str, BreadcrumbSection] = field(default_factory=dict)
    models: tuple[str, ...] = ()

    @property
    def blueprint(self) -> Blueprint:
        module_path, name = self.blueprint_path.split(":")
        return getattr(importlib.import_module(module_path), name)


ADMIN_EXTENSIONS: tuple[AdminExtension, ...] = (
    AdminExtension(
        key="admin",
        title="Пользователи",
        blueprint_path="app.modules.admin:admin_bp",
        menu=(MenuSection("Основное", (
            MenuItem("Пользователи", "admin.users_list", (
                "admin.users_list", "admin.user_create", "admin.user_edit",
            )),
            MenuItem("Группы", "admin.groups_list", (
                "admin.groups_list", "admin.group_create", "admin.group_edit",
            )),
        )),),
        breadcrumbs={
            "users": BreadcrumbSection(
                "Пользователи", "пользователя", "admin.users_list",
                "app.modules.auth.models.User", "username",
            ),
            "groups": BreadcrumbSection(
                "Группы", "группы", "admin.groups_list",
                "app.modules.auth.models.UserGroup",
            ),
        },
        models=("app.modules.auth.models",),
    ),
    AdminExtension(
        key="settings",
        title="Настройки",
        blueprint_path="app.modules.settings:settings_bp",
        menu=(MenuSection("Основное", (
            MenuItem("Настройки", "settings.settings_edit"),
        )),),
        models=("app.modules.settings.models",),
    ),
    AdminExtension(
        key="feedback",
        title="Обратная связь",
        blueprint_path="app.modules.feedback:feedback_admin_bp",
        menu=(MenuSection("Основное", (
            MenuItem("Обратная связь", "feedback_admin.feedback_list", (
                "feedback_admin.feedback_list",
                "feedback_admin.feedback_edit",
                "feedback_admin.feedback_delete",
            )),
        )),),
        breadcrumbs={
            "feedback": BreadcrumbSection(
                "Обратная связь", "обращения", "feedback_admin.feedback_list",
                "app.modules.feedback.models.Feedback", "title",
            ),
        },
        models=("app.modules.feedback.models",),
    ),
    AdminExtension(
        key="reports",
        title="Отчёты",
        blueprint_path="app.modules.reports:reports_bp",
        menu=(MenuSection("Отчёты", (
            MenuItem("Отчёты", "reports.reports_list", (
                "reports.reports_list",
                "reports.report_create",
                "reports.report_download",
                "reports.report_delete",
            )),
        )),),
        breadcrumbs={
            "reports": BreadcrumbSection(
                "Отчёты", "отчёта", "reports.reports_list",
                "app.modules.reports.models.Report", "name",
            ),
        },
        models=("app.modules.reports.models",),
    ),
    AdminExtension(
        key="catalog",
        title="Каталог",
        blueprint_path="app.modules.catalog:catalog_bp",
        menu=(MenuSection("Маркетплейс", (
            MenuItem("Товары", "catalog.products_list", (
                "catalog.products_list", "catalog.product_create", "catalog.product_edit",
                "catalog.import_ozon",
            )),
            MenuItem("Категории", "catalog.categories_list", (
                "catalog.categories_list", "catalog.category_create", "catalog.category_edit",
            )),
            MenuItem("Примитивы", "catalog.primitives_list", (
                "catalog.primitives_list", "catalog.primitive_create", "catalog.primitive_edit",
            )),
            MenuItem("Магазины", "catalog.marketplaces_list", (
                "catalog.marketplaces_list", "catalog.marketplace_create", "catalog.marketplace_edit",
            )),
        )),),
        breadcrumbs={
            "products": BreadcrumbSection(
                "Товары", "товара", "catalog.products_list",
                "app.modules.catalog.models.Product",
            ),
            "categories": BreadcrumbSection(
                "Категории", "категории", "catalog.categories_list",
                "app.modules.catalog.models.Category",
            ),
            "primitives": BreadcrumbSection(
                "Примитивы", "примитива", "catalog.primitives_list",
                "app.modules.catalog.models.Primitive",
            ),
            "marketplaces": BreadcrumbSection(
                "Маркетплейсы", "маркетплейса", "catalog.marketplaces_list",
                "app.modules.catalog.models.Marketplace",
            ),
        },
        models=("app.modules.catalog.models",),
    ),
)


def get_admin_menu() -> tuple[MenuSection, ...]:
    """Собирает меню всех расширений, объединяя секции с одинаковым заголовком."""
    sections: dict[str, list[MenuItem]] = {}
    for extension in ADMIN_EXTENSIONS:
        for section in extension.menu:
            sections.setdefault(section.title, []).extend(section.items)
    return tuple(MenuSection(title, tuple(items)) for title, items in sections.items())


def get_breadcrumb_sections() -> dict[str, BreadcrumbSection]:
    """Возвращает описания разделов всех расширений для хлебных крошек."""
    sections: dict[str, BreadcrumbSection] = {}
    for extension in ADMIN_EXTENSIONS:
        sections.update(extension.breadcrumbs)
    return sections
