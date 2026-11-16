"""Формы административной панели."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from app.modules.settings.constants import GROUP_CHOICES, USER_GROUP_ID


class CreateUserForm(FlaskForm):
    """Создание пользователя администратором."""

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


class UserGroupForm(FlaskForm):
    """Создание и редактирование группы пользователей."""

    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    slug = StringField("Slug", validators=[Length(max=255)])
    active = BooleanField("Группа активна", default=True)
    submit = SubmitField("Сохранить")