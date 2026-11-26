"""Формы отчётов."""

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import Optional


class ReportForm(FlaskForm):
    """Форма создания отчёта."""

    report_key = SelectField("Отчёт", choices=[], validators=[])
    category_id = SelectField("Категория", coerce=int, choices=[], validators=[Optional()])
    marketplace_id = SelectField("Магазин", coerce=int, choices=[], validators=[Optional()])
    submit = SubmitField("Сгенерировать")