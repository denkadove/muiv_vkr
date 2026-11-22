"""Формы настроек приложения."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import URL, Optional, NumberRange


class SettingsForm(FlaskForm):
    """Настройки приложения."""

    feed_url = StringField("URL фида примитивов", validators=[Optional(), URL()])
    tiny_api_key = StringField("TinyMCE API key", validators=[Optional()])
    dollar_exchange_rate = FloatField("Курс доллара", validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField("Сохранить")
