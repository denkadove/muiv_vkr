"""Публичные маршруты формы обратной связи."""

import random
from datetime import datetime, timezone

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from app.extensions import db
from app.modules.feedback import feedback_bp
from app.modules.feedback.forms import FeedbackForm
from app.modules.feedback.models import Feedback


def _generate_captcha() -> tuple[str, int]:
    """Генерирует простой математический пример для капчи."""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op = random.choice(("+", "-"))
    if op == "+":
        result = a + b
        question = f"{a} + {b} = ?"
    else:
        if a < b:
            a, b = b, a
        result = a - b
        question = f"{a} - {b} = ?"
    return question, result


@feedback_bp.route("/feedback", methods=["GET"])
def feedback_page() -> str:
    """Страница с формой обратной связи."""
    return render_template("feedback.html")


@feedback_bp.route("/feedback", methods=["POST"])
def feedback_create() -> str:
    """Создаёт обращение из публичной формы."""
    form = FeedbackForm()
    if not form.validate_on_submit():
        flash("Проверьте правильность заполнения формы.", "error")
        return redirect(url_for("index"))

    # Капча для неавторизованных
    if not current_user.is_authenticated:
        expected = session.get("captcha_answer")
        if expected is None or str(form.captcha.data).strip() != str(expected):
            flash("Неверный ответ на капчу.", "error")
            return redirect(url_for("index"))

    feedback = Feedback(
        title=form.title.data.strip(),
        text=form.text.data.strip(),
        email=form.email.data.strip(),
        type=form.type.data,
        user_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(feedback)
    db.session.commit()

    # Очищаем капчу
    session.pop("captcha_answer", None)

    flash("Ваше обращение отправлено. Спасибо!", "success")
    return redirect(url_for("index"))


@feedback_bp.app_context_processor
def inject_captcha():
    """Генерирует капчу для анонимов на главной странице (только GET)."""
    from flask import request

    if not current_user.is_authenticated and request.method == "GET":
        question, answer = _generate_captcha()
        session["captcha_answer"] = answer
        session["captcha_question"] = question
        return {"captcha_question": question}
    return {"captcha_question": session.get("captcha_question")}