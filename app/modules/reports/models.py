"""Модель отчёта."""

from datetime import datetime, timezone

from app.extensions import db


class Report(db.Model):
    """Сгенерированный отчёт (файл xlsx)."""

    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    report_key = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="pending")
    filters = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", backref="reports")