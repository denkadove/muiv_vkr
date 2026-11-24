"""Административные маршруты обратной связи."""

from datetime import datetime

from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from app.extensions import db
from app.modules.auth.decorators import admin_required
from app.modules.feedback import feedback_admin_bp
from app.modules.feedback.forms import FeedbackEditForm
from app.modules.feedback.models import Feedback


@feedback_admin_bp.route("")
@admin_required
def feedback_list():
    """Список обращений с фильтрами."""
    status = request.args.get("status", "").strip()
    ftype = request.args.get("type", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    query = Feedback.query.filter_by(active=True)

    if status:
        query = query.filter(Feedback.status == status)
    if ftype:
        query = query.filter(Feedback.type == ftype)
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Feedback.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Feedback.created_at <= dt_to)
        except ValueError:
            pass

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = query.order_by(Feedback.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    feedbacks = pagination.items

    return render_template(
        "feedback/list.html",
        feedbacks=feedbacks,
        pagination=pagination,
        status=status,
        ftype=ftype,
        date_from=date_from,
        date_to=date_to,
        Feedback=Feedback,
    )


@feedback_admin_bp.route("/<int:feedback_id>", methods=["GET", "POST"])
@admin_required
def feedback_edit(feedback_id):
    """Просмотр и редактирование обращения."""
    feedback = db.session.get(Feedback, feedback_id)
    if feedback is None or not feedback.active:
        flash("Обращение не найдено.", "error")
        return redirect(url_for("feedback_admin.feedback_list"))

    form = FeedbackEditForm()
    if request.method == "GET":
        form.status.data = feedback.status
        form.admin_comment.data = feedback.admin_comment

    if form.validate_on_submit():
        feedback.status = form.status.data
        feedback.admin_comment = form.admin_comment.data
        db.session.commit()
        flash("Обращение обновлено.", "success")
        return redirect(url_for("feedback_admin.feedback_list"))

    return render_template(
        "feedback/edit.html",
        feedback=feedback,
        form=form,
        Feedback=Feedback,
    )


@feedback_admin_bp.route("/<int:feedback_id>/delete", methods=["POST"])
@admin_required
def feedback_delete(feedback_id):
    """Мягкое удаление обращения (active=False)."""
    feedback = db.session.get(Feedback, feedback_id)
    if feedback is None:
        flash("Обращение не найдено.", "error")
        return redirect(url_for("feedback_admin.feedback_list"))

    feedback.active = False
    db.session.commit()
    flash("Обращение удалено.", "success")
    return redirect(url_for("feedback_admin.feedback_list"))