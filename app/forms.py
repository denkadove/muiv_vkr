"""Формы WTForms для аутентификации."""

from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    StringField,
    SubmitField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length


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
    """Создание пользователя администратором (в разработке)."""

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
    active = True
    group_id = 1
    submit = SubmitField("Создать пользователя")
