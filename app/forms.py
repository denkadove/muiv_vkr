from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    StringField,
    SubmitField,
    BooleanField,
    HiddenField,
)

from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

class RegisterForm(FlaskForm):
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

    group_id = HiddenField("Группа", default=1)

    agree_personal_data = BooleanField(
        "Согласие на обработку персональных данных",
        validators=[DataRequired(message="Необходимо согласие на обработку персональных данных")],
    )

    submit = SubmitField("Регистрация")


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class CreateUserForm(FlaskForm):
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
