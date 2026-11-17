"""Формы настроек приложения."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import URL, Optional


class SettingsForm(FlaskForm):
    """Настройки приложения."""

    feed_url = StringField("URL фида примитивов", validators=[Optional(), URL()])
    submit = SubmitField("Сохранить")