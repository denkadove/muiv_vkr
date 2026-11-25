"""Декораторы контроля доступа."""

from collections.abc import Callable
from functools import wraps

from flask import Response, flash, redirect, url_for
from flask_login import current_user, login_required

from app.modules.settings.constants import ADMIN_GROUP_ID, MANAGER_GROUP_ID, USER_GROUP_ID


def admin_required(
    view: Callable[..., Response | str],
) -> Callable[..., Response | str]:
    """Ограничивает доступ к маршруту администраторами (группа 1)."""

    @wraps(view)
    @login_required
    def wrapped_view(*args: object, **kwargs: object) -> Response | str:
        if current_user.group_id != ADMIN_GROUP_ID:
            flash("Доступ только для администраторов.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def manager_required(
    view: Callable[..., Response | str],
) -> Callable[..., Response | str]:
    """Ограничивает доступ к маршруту администраторами и менеджерами."""

    @wraps(view)
    @login_required
    def wrapped_view(*args: object, **kwargs: object) -> Response | str:
        if current_user.group_id not in (ADMIN_GROUP_ID, MANAGER_GROUP_ID):
            flash("Доступ только для администраторов и менеджеров.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(
    *roles: int,
) -> Callable[[Callable[..., Response | str]], Callable[..., Response | str]]:
    """Ограничивает доступ к маршруту указанными группами."""

    def decorator(view: Callable[..., Response | str]) -> Callable[..., Response | str]:
        @wraps(view)
        @login_required
        def wrapped_view(*args: object, **kwargs: object) -> Response | str:
            if current_user.group_id not in roles:
                flash("Недостаточно прав для доступа.", "error")
                return redirect(url_for("index"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator