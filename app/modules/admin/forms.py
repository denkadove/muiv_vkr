"""Формы административной панели."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional

from app.modules.settings.constants import GROUP_CHOICES, USER_GROUP_ID


class CreateUserForm(FlaskForm):
    """Создание пользователя администратором."""

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
    active = BooleanField("Учётная запись активна", default=True)
    group_id = SelectField("Группа", coerce=int, choices=GROUP_CHOICES, default=USER_GROUP_ID)
    submit = SubmitField("Создать пользователя")


class UserForm(FlaskForm):
    """Редактирование пользователя администратором (без смены пароля)."""

    username = StringField("Логин", validators=[DataRequired(message="Поле обязательно для заполнения."), Length(min=3, max=255, message="От 3 до 255 символов.")])
    email = StringField("Email", validators=[DataRequired(message="Поле обязательно для заполнения."), Email(message="Введите корректный email.")])
    name = StringField("Имя", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    phone = StringField("Телефон", validators=[Optional(), Length(max=50, message="Не более 50 символов.")])
    position = StringField("Должность", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    department = StringField("Отдел", validators=[Optional(), Length(max=255, message="Не более 255 символов.")])
    active = BooleanField("Учётная запись активна")
    group_id = SelectField("Группа", coerce=int, choices=GROUP_CHOICES)
    submit = SubmitField("Сохранить")


class UserGroupForm(FlaskForm):
    """Создание и редактирование группы пользователей."""

    name = StringField("Название", validators=[DataRequired(message="Поле обязательно для заполнения."), Length(max=255, message="Не более 255 символов.")])
    slug = StringField("Slug", validators=[Length(max=255, message="Не более 255 символов.")])
    active = BooleanField("Группа активна", default=True)
    submit = SubmitField("Сохранить")