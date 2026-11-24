"""Блюпринты формы обратной связи: публичная форма и админка."""

from flask import Blueprint

feedback_bp = Blueprint(
    "feedback", __name__, template_folder="templates", url_prefix=""
)

feedback_admin_bp = Blueprint(
    "feedback_admin", __name__, template_folder="templates", url_prefix="/admin/feedback"
)

# Импортируем маршруты после создания блюпринтов
from app.modules.feedback import routes  # noqa: E402, F401
from app.modules.feedback import admin_routes  # noqa: E402, F401