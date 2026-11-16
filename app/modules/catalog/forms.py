"""Формы каталога."""

from flask_wtf import FlaskForm
from wtforms import DecimalField, IntegerField, StringField, SubmitField, TextAreaField, SelectField, SelectMultipleField, FieldList, FormField
from wtforms.validators import DataRequired, Length, NumberRange


class PrimitiveLineForm(FlaskForm):
    """Строка состава товара: примитив + количество."""

    primitive_id = SelectField("Примитив", coerce=int, validators=[DataRequired()])
    quantity = IntegerField("Кол-во", validators=[DataRequired(), NumberRange(min=1)], default=1)


class ProductForm(FlaskForm):
    """Создание и редактирование товара."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    category_id = SelectField("Категория", coerce=int)
    marketplaces = SelectMultipleField("Маркетплейсы", coerce=int)
    description = TextAreaField("Описание")
    composition = FieldList(FormField(PrimitiveLineForm), min_entries=1)
    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    """Создание и редактирование категории."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    submit = SubmitField("Сохранить")


class PrimitiveForm(FlaskForm):
    """Создание и редактирование примитива."""

    sku = StringField("Артикул (SKU)", validators=[DataRequired(), Length(max=255)])
    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    price = DecimalField("Цена", validators=[DataRequired(), NumberRange(min=0)], places=2)
    stock = IntegerField("Остаток", validators=[DataRequired(), NumberRange(min=0)], default=0)
    submit = SubmitField("Сохранить")


class MarketplaceForm(FlaskForm):
    """Создание и редактирование маркетплейса."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    api_key = StringField("Api-ключ", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")