"""Формы настроек приложения."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import URL, Optional, NumberRange, DataRequired


class SettingsForm(FlaskForm):
    """Настройки приложения."""

    feed_url = StringField("URL фида примитивов", validators=[Optional(), URL(message="Введите корректный URL.")])
    tiny_api_key = StringField("TinyMCE API key", validators=[Optional()])
    dollar_exchange_rate = FloatField("Курс доллара", validators=[Optional(), NumberRange(min=0, message="Значение не может быть отрицательным.")])
    submit = SubmitField("Сохранить")


class ExchangeRateForm(FlaskForm):
    """Форма изменения курса доллара (доступна менеджерам)."""

    dollar_exchange_rate = FloatField(
        "Курс доллара",
        validators=[DataRequired(message="Поле обязательно для заполнения."), NumberRange(min=0, message="Значение не может быть отрицательным.")],
    )
    submit = SubmitField("Сохранить")
