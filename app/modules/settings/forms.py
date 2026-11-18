"""Формы настроек приложения."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import URL, Optional


class SettingsForm(FlaskForm):
    """Настройки приложения."""

    feed_url = StringField("URL фида примитивов", validators=[Optional(), URL()])
    tiny_api_key = StringField("TinyMCE API key", validators=[Optional()])
    submit = SubmitField("Сохранить")