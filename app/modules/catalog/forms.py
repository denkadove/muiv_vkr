"""Формы каталога."""

from flask_wtf import FlaskForm

from app.extensions import db
from wtforms import BooleanField, DecimalField, FloatField, HiddenField, IntegerField, StringField, SubmitField, TextAreaField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL, ValidationError
from flask_wtf.file import FileField, MultipleFileField


class MarketplaceStatusForm(FlaskForm):
    """Строка статуса размещения на маркетплейсе."""

    marketplace_id = HiddenField()
    external_offer_id = StringField("Offer ID", validators=[Length(max=255)])
    status = SelectField("Статус", choices=[
        ("v", "Размещён"),
        ("o", "На модерации"),
        ("x", "Не размещён"),
        ("N", "Снят"),
    ], default="x")


class PrimitiveLineForm(FlaskForm):
    """Строка состава товара: примитив + количество."""

    primitive_id = StringField("Примитив", validators=[DataRequired()])
    quantity = IntegerField("Кол-во", validators=[DataRequired(), NumberRange(min=1)], default=1)

    def validate_primitive_id(self, field):
        value = (field.data or "").strip()
        if not value:
            raise ValidationError("Выберите примитив из списка.")
        from app.modules.catalog.models import Primitive
        # Поддержка формата "sku — name" или просто sku/name/id
        pid = None
        if value.isdigit():
            pid = int(value)
            prim = db.session.get(Primitive, pid)
        else:
            sku_part = value.split("—")[0].strip() if "—" in value else value
            prim = Primitive.query.filter(
                (Primitive.sku == sku_part) | (Primitive.name == value)
            ).first()
            if prim is None:
                # поиск по частичному совпадению названия
                prim = Primitive.query.filter(Primitive.name.ilike(f"%{value}%")).first()
        if prim is None:
            raise ValidationError("Примитив не найден.")
        # Сохраняем id в data для сервиса
        field.data = str(prim.id)


class ProductForm(FlaskForm):
    """Создание и редактирование товара."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    sku = StringField("Артикул (SKU)", validators=[Length(max=255)])
    barcode = StringField("Штрихкод", validators=[Length(max=32)])
    selling_price = DecimalField("Цена продажи", validators=[Optional(), NumberRange(min=0)], places=2)
    weight = FloatField("Вес, кг", validators=[Optional(), NumberRange(min=0)])
    length = FloatField("Длина, см", validators=[Optional(), NumberRange(min=0)])
    width = FloatField("Ширина, см", validators=[Optional(), NumberRange(min=0)])
    height = FloatField("Высота, см", validators=[Optional(), NumberRange(min=0)])
    brand = StringField("Бренд", validators=[Length(max=255)])
    country = StringField("Страна", validators=[Length(max=255)])
    warranty = StringField("Гарантия", validators=[Length(max=255)])
    video_url = StringField("Ссылка на видео", validators=[Optional(), URL(), Length(max=500)])
    certificate = FileField("Сертификат соответствия")
    images = MultipleFileField("Фото товара")
    active = BooleanField("Товар активен", default=True)
    category_id = SelectField("Категория", coerce=int)
    marketplace_statuses = FieldList(FormField(MarketplaceStatusForm))
    description = TextAreaField("Описание")
    composition = FieldList(FormField(PrimitiveLineForm), min_entries=1)
    submit = SubmitField("Сохранить")


class CategoryForm(FlaskForm):
    """Создание и редактирование категории."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    active = BooleanField("Категория активна", default=True)
    sort_order = IntegerField("Порядок сортировки", default=0)
    processing_cost = DecimalField("Стоимость обработки, руб", validators=[NumberRange(min=0)], places=2, default=0)
    coinvest_factor = DecimalField("Коэф. соинвеста", validators=[NumberRange(min=0)], places=2, default=0.5)
    submit = SubmitField("Сохранить")


class PrimitiveForm(FlaskForm):
    """Создание и редактирование примитива."""

    sku = StringField("Артикул (SKU)", validators=[DataRequired(), Length(max=255)])
    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    price = DecimalField("Цена", validators=[DataRequired(), NumberRange(min=0)], places=2)
    submit = SubmitField("Сохранить")


class MarketplaceForm(FlaskForm):
    """Создание и редактирование маркетплейса."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    marketplace_type = SelectField("Тип магазина", choices=[
        ("Яндекс", "Яндекс"),
        ("Озон", "Озон"),
        ("WB", "WB"),
    ], validators=[DataRequired()])
    api_key = StringField("Api-ключ", validators=[DataRequired(), Length(max=255)])
    client_id = StringField("Client-Id (Ozon)", validators=[Optional(), Length(max=255)])
    description = TextAreaField("Описание")
    submit = SubmitField("Сохранить")