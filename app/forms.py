"""Формы WTForms для аутентификации и администрирования."""

from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    StringField,
    SubmitField,
    BooleanField,
    SelectField,
    SelectMultipleField,
    TextAreaField,
    DecimalField,
)


from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange

from app.models import ADMIN_GROUP_ID, USER_GROUP_ID

# Выбор группы из констант: заменить на запрос к БД
GROUP_CHOICES: list[tuple[int, str]] = [
    (ADMIN_GROUP_ID, "Администратор"),
    (USER_GROUP_ID, "Пользователь"),
]

# CATEGORY_CHOICES: list[tuple[int, str]] = [
#     (1, "Мелкогаборит"),
#     (2, "Крупногабарит"),
# ]

class RegisterForm(FlaskForm):
    """Регистрация: логин, email, пароли, согласие на обработку данных."""

    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=255)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Подтверждение пароля",
        validators=[
            DataRequired(),
            EqualTo("password", message="Пароли должны совпадать"),
        ],
    )

    agree_personal_data = BooleanField(
        "Согласие на обработку персональных данных",
        validators=[DataRequired(message="Необходимо согласие на обработку персональных данных")],
    )

    submit = SubmitField("Регистрация")


class LoginForm(FlaskForm):
    """Вход в систему: логин и пароль."""

    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class CreateUserForm(FlaskForm):
    """Создание пользователя администратором: группа и активность задаются формой."""

    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=255)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Подтверждение пароля",
        validators=[
            DataRequired(),
            EqualTo("password", message="Пароли должны совпадать"),
        ],
    )
    active = BooleanField("Учётная запись активна", default=True)
    group_id = SelectField("Группа", coerce=int, choices=GROUP_CHOICES, default=USER_GROUP_ID)
    submit = SubmitField("Создать пользователя")


class UserForm(FlaskForm):
    """Редактирование пользователя администратором (без смены пароля)."""

    username = StringField("Логин", validators=[DataRequired(), Length(min=3, max=255)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    active = BooleanField("Учётная запись активна")
    group_id = SelectField("Группа", coerce=int, choices=GROUP_CHOICES)
    submit = SubmitField("Сохранить")


class ProductForm(FlaskForm):
    """Создание и редактирование товара.

    Особенности:
        - варианты категорий задаются в маршруте (список зависит от БД).
    """

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