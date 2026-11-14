"""Сервисный слой: бизнес-логика, независимая от HTTP."""

from sqlalchemy.exc import IntegrityError

from app import bcrypt, db
from app.forms import CreateUserForm, RegisterForm, UserEditForm
from app.models import ADMIN_GROUP_ID, USER_GROUP_ID, User


def _hash_password(password: str) -> str:
    """Хэширует пароль алгоритмом bcrypt.

    Аргументы:
        password (str): пароль в открытом виде.

    Возвращает:
        str: строка bcrypt-хэша.
    """
    return bcrypt.generate_password_hash(password).decode("utf-8")


def _ensure_free_credentials(username: str, email: str) -> None:
    """Проверяет, что логин и email не заняты другими пользователями.

    Аргументы:
        username (str): логин.
        email (str): email.

    Исключения:
        ValueError: логин или email уже заняты.
    """
    if User.query.filter_by(username=username).first() is not None:
        raise ValueError("Пользователь с таким логином уже существует.")
    if User.query.filter_by(email=email).first() is not None:
        raise ValueError("Пользователь с таким email уже существует.")


def _is_last_active_admin(user: User) -> bool:
    """Определяет, является ли пользователь последним активным администратором.

    Аргументы:
        user (User): проверяемый пользователь.

    Возвращает:
        bool: True, если пользователь — активный администратор
        и других активных администраторов в системе нет.
    """
    if user.group_id != ADMIN_GROUP_ID or not user.active:
        return False
    return User.query.filter_by(group_id=ADMIN_GROUP_ID, active=True).count() == 1


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
    _ensure_free_credentials(form.username.data, form.email.data)

    is_first_user: bool = User.query.count() == 0
    group_id: int = ADMIN_GROUP_ID if is_first_user else USER_GROUP_ID

    user = User(
        username=form.username.data,
        email=form.email.data,
        password=_hash_password(form.password.data),
        group_id=group_id,
    )
    db.session.add(user)
    # Проверка уникальности не атомарна: дубликат ловим по ограничению БД
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Пользователь с таким логином или email уже существует.")
    return user


def admin_create_user(form: CreateUserForm) -> User:
    """Создаёт пользователя по решению администратора.

    Особенности:
        - группа и активность берутся из формы, а не из счётчика пользователей.

    Аргументы:
        form (CreateUserForm): форма создания пользователя.

    Возвращает:
        User: созданный пользователь, сохранённый в базе.

    Исключения:
        ValueError: логин или email уже заняты.
    """
    _ensure_free_credentials(form.username.data, form.email.data)

    user = User(
        username=form.username.data,
        email=form.email.data,
        password=_hash_password(form.password.data),
        group_id=form.group_id.data,
        active=form.active.data,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Пользователь с таким логином или email уже существует.")
    return user


def admin_update_user(user_id: int, form: UserEditForm) -> User:
    """Обновляет данные пользователя (без смены пароля).

    Особенности:
        - уникальность логина/email проверяется с исключением самого пользователя;
        - нельзя лишить прав или деактивировать последнего активного администратора.

    Аргументы:
        user_id (int): идентификатор редактируемого пользователя.
        form (UserEditForm): форма с новыми данными.

    Возвращает:
        User: обновлённый пользователь.

    Исключения:
        LookupError: пользователь не найден.
        ValueError: логин или email заняты другим пользователем либо
        нарушен инвариант последнего активного администратора.
    """
    user: User | None = db.session.get(User, user_id)
    if user is None:
        raise LookupError("Пользователь не найден.")

    if User.query.filter(User.username == form.username.data, User.id != user_id).first() is not None:
        raise ValueError("Пользователь с таким логином уже существует.")
    if User.query.filter(User.email == form.email.data, User.id != user_id).first() is not None:
        raise ValueError("Пользователь с таким email уже существует.")

    losing_admin_rights: bool = user.group_id == ADMIN_GROUP_ID and (
        form.group_id.data != ADMIN_GROUP_ID or not form.active.data
    )
    if losing_admin_rights and _is_last_active_admin(user):
        raise ValueError(
            "Нельзя лишить прав или деактивировать последнего активного администратора."
        )

    user.username = form.username.data
    user.email = form.email.data
    user.active = form.active.data
    user.group_id = form.group_id.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Пользователь с таким логином или email уже существует.")
    return user


def delete_user(user_id: int, admin_id: int) -> None:
    """Удаляет пользователя из системы.

    Особенности:
        - администратор не может удалить сам себя;
        - нельзя удалить последнего активного администратора.

    Аргументы:
        user_id (int): идентификатор удаляемого пользователя.
        admin_id (int): идентификатор администратора, выполняющего удаление.

    Исключения:
        LookupError: пользователь не найден.
        ValueError: попытка удалить себя или последнего активного администратора.
    """
    if user_id == admin_id:
        raise ValueError("Нельзя удалить собственную учётную запись.")

    user: User | None = db.session.get(User, user_id)
    if user is None:
        raise LookupError("Пользователь не найден.")

    if _is_last_active_admin(user):
        raise ValueError("Нельзя удалить последнего активного администратора.")

    db.session.delete(user)
    db.session.commit()
