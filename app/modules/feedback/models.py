"""Модель обращения обратной связи."""

from datetime import datetime, timezone

from app.extensions import db


class Feedback(db.Model):
    """Обращение пользователя (вопрос, предложение, ошибка)."""

    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    text = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False, default="question")
    status = db.Column(db.String(50), nullable=False, default="new")
    admin_comment = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref="feedbacks")

    FEEDBACK_TYPES = [
        ("question", "Вопрос"),
        ("suggestion", "Предложение"),
        ("bug", "Сообщить об ошибке"),
    ]

    STATUSES = [
        ("new", "Новое"),
        ("viewed", "Просмотрено"),
        ("in_progress", "В работе"),
        ("done", "Завершено"),
    ]