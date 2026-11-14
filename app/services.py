"""Сервисный слой: бизнес-логика, независимая от HTTP."""

from app import bcrypt, db
from app.forms import RegisterForm
from app.models import User

# Группа 1 — администратор, группа 2 — обычный пользователь
ADMIN_GROUP_ID: int = 1
USER_GROUP_ID: int = 2


def create_user(form: RegisterForm) -> User:
    """Создаёт пользователя из провалидированной формы регистрации.

    Особенности:
        - первый пользователь системы получает группу администратора;
        - пароль сохраняется только в виде bcrypt-хэша.

    Аргументы:
        form (RegisterForm): форма регистрации с данными пользователя.

    Возвращает:
        User: созданный пользователь, сохранённый в базе.

    Исключения:
        ValueError: логин или email уже заняты.
    """
    if User.query.filter_by(username=form.username.data).first() is not None:
        raise ValueError("Пользователь с таким логином уже существует.")
    if User.query.filter_by(email=form.email.data).first() is not None:
        raise ValueError("Пользователь с таким email уже существует.")

    hashed_password: str = bcrypt.generate_password_hash(
        form.password.data
    ).decode("utf-8")

    is_first_user: bool = User.query.count() == 0
    group_id: int = ADMIN_GROUP_ID if is_first_user else USER_GROUP_ID

    user = User(
        username=form.username.data,
        email=form.email.data,
        password=hashed_password,
        group_id=group_id,
    )
    db.session.add(user)
    db.session.commit()
    return user
