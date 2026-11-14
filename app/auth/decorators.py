"""Декораторы контроля доступа."""

from collections.abc import Callable
from functools import wraps

from flask import Response, flash, redirect, url_for
from flask_login import current_user, login_required

from app.models import ADMIN_GROUP_ID


def admin_required(
    view: Callable[..., Response | str],
) -> Callable[..., Response | str]:
    """Ограничивает доступ к маршруту администраторами (группа 1).

    Особенности:
        - неавторизованных перенаправляет на страницу входа;
        - остальным пользователям показывает flash и возвращает на главную.

    Аргументы:
        view (Callable): функция представления.

    Возвращает:
        Callable: декорированное представление.
    """

    @wraps(view)
    @login_required
    def wrapped_view(*args: object, **kwargs: object) -> Response | str:
        """Проверяет группу пользователя и запускает исходный маршрут."""
        if current_user.group_id != ADMIN_GROUP_ID:
            flash("Доступ только для администраторов.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view
