"""Формы каталога."""

from flask_wtf import FlaskForm
from wtforms import DecimalField, StringField, SubmitField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange


class ProductForm(FlaskForm):
    """Создание и редактирование товара."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    price = DecimalField("Цена", validators=[DataRequired(), NumberRange(min=0)], places=2)
    category_id = SelectField("Категория", coerce=int)
    marketplaces = SelectMultipleField("Маркетплейсы", coerce=int)
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    """Создание и редактирование категории."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Сохранить")


class MarketplaceForm(FlaskForm):
    """Создание и редактирование маркетплейса."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    api_key = StringField("Api-ключ", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")