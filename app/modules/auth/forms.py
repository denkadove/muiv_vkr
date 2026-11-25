"""Формы аутентификации."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app.modules.settings.constants import GROUP_CHOICES


class RegisterForm(FlaskForm):
    """Регистрация: логин, email, пароли, согласие на обработку данных."""

    username = StringField("Логин", validators=[DataRequired(message="Поле обязательно для заполнения."), Length(min=3, max=255, message="От 3 до 255 символов.")])
    email = StringField("Email", validators=[DataRequired(message="Поле обязательно для заполнения."), Email(message="Введите корректный email.")])
    password = PasswordField("Пароль", validators=[DataRequired(message="Поле обязательно для заполнения."), Length(min=6, message="Не менее 6 символов.")])
    confirm_password = PasswordField(
        "Подтверждение пароля",
        validators=[
            DataRequired(message="Поле обязательно для заполнения."),
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

    username = StringField("Логин", validators=[DataRequired(message="Поле обязательно для заполнения.")])
    password = PasswordField("Пароль", validators=[DataRequired(message="Поле обязательно для заполнения.")])
    remember_me = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class ProfileForm(FlaskForm):
    """Редактирование профиля пользователя."""

    name = StringField("Имя", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    phone = StringField("Телефон", validators=[Optional(), Length(max=50, message="Не более 50 символов.")])
    position = StringField("Должность", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    department = StringField("Отдел", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    avatar = FileField("Аватар")
    email = StringField("Email", validators=[Optional(), Email(message="Введите корректный email.")])
    group_id = SelectField("Группа", coerce=int, choices=GROUP_CHOICES, validators=[Optional()])
    password = PasswordField("Новый пароль", validators=[Optional(), Length(min=6, message="Не менее 6 символов.")])
    confirm_password = PasswordField(
        "Подтверждение пароля",
        validators=[EqualTo("password", message="Пароли должны совпадать")],
    )
    submit = SubmitField("Сохранить")