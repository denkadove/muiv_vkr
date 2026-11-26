"""Маршруты отчётов."""

import os

from flask import (
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user

from app.extensions import db
from app.modules.auth.decorators import manager_required
from app.modules.catalog.models import Category, Marketplace
from app.modules.reports import reports_bp
from app.modules.reports.forms import ReportForm
from app.modules.reports.models import Report
from app.modules.reports.registry import REPORTS
from app.modules.reports.services import generate_catalog_report


@reports_bp.route("")
@manager_required
def reports_list():
    """Список сгенерированных отчётов."""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = (
        Report.query.filter_by(active=True)
        .order_by(Report.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    reports = pagination.items
    return render_template(
        "reports/list.html",
        reports=reports,
        pagination=pagination,
    )


@reports_bp.route("/create", methods=["GET", "POST"])
@manager_required
def report_create():
    """Создание отчёта."""
    form = ReportForm()
    form.report_key.choices = [(r.key, r.title) for r in REPORTS]
    form.category_id.choices = [(0, "Все категории")] + [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]
    form.marketplace_id.choices = [(0, "Все магазины")] + [
        (m.id, m.short_name or m.name) for m in Marketplace.query.order_by(Marketplace.name).all()
    ]

    if form.validate_on_submit():
        report_key = form.report_key.data
        category_id = form.category_id.data or None
        marketplace_id = form.marketplace_id.data or None
        if category_id == 0:
            category_id = None
        if marketplace_id == 0:
            marketplace_id = None

        report_def = next((r for r in REPORTS if r.key == report_key), None)
        if report_def is None:
            flash("Отчёт не найден.", "error")
            return redirect(url_for("reports.report_create"))

        filters = {"category_id": category_id, "marketplace_id": marketplace_id}
        try:
            file_path = report_def.generator(filters)
        except Exception as error:
            flash(f"Ошибка генерации: {error}", "error")
            return redirect(url_for("reports.report_create"))

        # Проверяем, что отчёт не пустой
        from openpyxl import load_workbook

        wb = load_workbook(file_path)
        ws = wb.active
        if ws.max_row <= 1:
            flash("Отчёт сгенерирован, но по выбранным фильтрам товары не найдены.", "warning")
        else:
            flash(f"Отчёт сгенерирован ({ws.max_row - 1} товаров).", "success")

        report = Report(
            name=report_def.title,
            report_key=report_key,
            file_path=file_path,
            status="ready",
            filters=filters,
            user_id=current_user.id,
        )
        db.session.add(report)
        db.session.commit()

        return redirect(url_for("reports.reports_list"))
        return redirect(url_for("reports.reports_list"))

    return render_template("reports/create.html", form=form, reports=REPORTS)


@reports_bp.route("/<int:report_id>/download")
@manager_required
def report_download(report_id):
    """Скачивание файла отчёта."""
    report = db.session.get(Report, report_id)
    if report is None or not report.active or not report.file_path:
        flash("Отчёт не найден.", "error")
        return redirect(url_for("reports.reports_list"))
    if not os.path.exists(report.file_path):
        flash("Файл отчёта не найден.", "error")
        return redirect(url_for("reports.reports_list"))
    return send_file(report.file_path, as_attachment=True)


@reports_bp.route("/<int:report_id>/delete", methods=["POST"])
@manager_required
def report_delete(report_id):
    """Мягкое удаление отчёта."""
    report = db.session.get(Report, report_id)
    if report is None:
        flash("Отчёт не найден.", "error")
        return redirect(url_for("reports.reports_list"))
    report.active = False
    db.session.commit()
    flash("Отчёт удалён.", "success")
    return redirect(url_for("reports.reports_list"))