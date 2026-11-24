"""Формы обратной связи."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length

from app.modules.feedback.models import Feedback


class FeedbackForm(FlaskForm):
    """Публичная форма отправки обращения."""

    title = StringField(
        "Заголовок",
        validators=[DataRequired(message="Поле обязательно для заполнения."), Length(max=255, message="Не более 255 символов.")],
    )
    text = TextAreaField(
        "Текст",
        validators=[DataRequired(message="Поле обязательно для заполнения.")],
    )
    email = StringField(
        "Email для обратной связи",
        validators=[DataRequired(message="Поле обязательно для заполнения."), Email(message="Введите корректный email.")],
    )
    type = SelectField(
        "Тип обращения",
        choices=Feedback.FEEDBACK_TYPES,
        validators=[DataRequired(message="Выберите тип обращения.")],
    )
    agree = BooleanField(
        "Согласен с политикой конфиденциальности",
        validators=[DataRequired(message="Необходимо согласие с политикой конфиденциальности.")],
    )
    captcha = StringField("Ответ на капчу")


class FeedbackEditForm(FlaskForm):
    """Форма редактирования обращения в админке."""

    status = SelectField(
        "Статус",
        choices=[
            ("new", "Новое"),
            ("viewed", "Просмотрено"),
            ("in_progress", "В работе"),
            ("done", "Завершено"),
        ],
        validators=[DataRequired(message="Выберите статус.")],
    )
    admin_comment = TextAreaField("Комментарий администратора")
    submit = SubmitField("Сохранить")