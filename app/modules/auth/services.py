"""Сервисный слой пользователей: бизнес-логика, независимая от HTTP."""

from sqlalchemy.exc import IntegrityError

from app.extensions import bcrypt, db
from app.modules.settings.constants import ADMIN_GROUP_ID, USER_GROUP_ID
from app.modules.auth.models import User, UserGroup


def _hash_password(password: str) -> str:
    """Хэширует пароль алгоритмом bcrypt."""
    return bcrypt.generate_password_hash(password).decode("utf-8")


def _ensure_free_credentials(username: str, email: str) -> None:
    """Проверяет, что логин и email не заняты другими пользователями."""
    if User.query.filter_by(username=username).first() is not None:
        raise ValueError("Пользователь с таким логином уже существует.")
    if User.query.filter_by(email=email).first() is not None:
        raise ValueError("Пользователь с таким email уже существует.")


def _is_last_active_admin(user: User) -> bool:
    """Определяет, является ли пользователь последним активным администратором."""
    if user.group_id != ADMIN_GROUP_ID or not user.active:
        return False
    return User.query.filter_by(group_id=ADMIN_GROUP_ID, active=True).count() == 1


def create_user(form, group_id=None, active=True) -> User:
    """Создаёт пользователя: служит и для регистрации, и для админ-панели."""
    _ensure_free_credentials(form.username.data, form.email.data)

    if group_id is None:
        is_first_user: bool = User.query.count() == 0
        group_id = ADMIN_GROUP_ID if is_first_user else USER_GROUP_ID

    user = User(
        username=form.username.data,
        email=form.email.data,
        password=_hash_password(form.password.data),
        group_id=group_id,
        active=active,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Пользователь с таким логином или email уже существует.")
    return user


def update_user(user_id: int, form) -> User:
    """Обновляет данные пользователя (без смены пароля)."""
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
    """Удаляет пользователя из системы."""
    if user_id == admin_id:
        raise ValueError("Нельзя удалить собственную учётную запись.")

    user: User | None = db.session.get(User, user_id)
    if user is None:
        raise LookupError("Пользователь не найден.")

    if _is_last_active_admin(user):
        raise ValueError("Нельзя удалить последнего активного администратора.")

    db.session.delete(user)
    db.session.commit()


def get_user_groups() -> list[UserGroup]:
    """Возвращает список групп пользователей."""
    if UserGroup.query.count() == 0:
        db.session.add(UserGroup(name="Администратор", slug="admin", active=True))
        db.session.add(UserGroup(name="Пользователь", slug="user", active=True))
        db.session.commit()
    return UserGroup.query.order_by(UserGroup.id).all()


def _slugify(value: str) -> str:
    """Простая транслитерация/нормализация в slug."""
    return value.strip().lower().replace(" ", "-")


def create_user_group(form) -> UserGroup:
    """Создаёт группу пользователей."""
    name = form.name.data.strip()
    slug = (form.slug.data or "").strip() or _slugify(name)
    if UserGroup.query.filter_by(name=name).first() is not None:
        raise ValueError("Группа с таким названием уже существует.")
    if UserGroup.query.filter_by(slug=slug).first() is not None:
        raise ValueError("Группа с таким slug уже существует.")

    group = UserGroup(name=name, slug=slug, active=form.active.data)
    db.session.add(group)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Группа с таким названием или slug уже существует.")
    return group


def update_user_group(group_id: int, form) -> UserGroup:
    """Обновляет группу пользователей."""
    group: UserGroup | None = db.session.get(UserGroup, group_id)
    if group is None:
        raise LookupError("Группа не найдена.")

    name = form.name.data.strip()
    slug = (form.slug.data or "").strip() or group.slug

    if UserGroup.query.filter(UserGroup.name == name, UserGroup.id != group_id).first() is not None:
        raise ValueError("Группа с таким названием уже существует.")
    if UserGroup.query.filter(UserGroup.slug == slug, UserGroup.id != group_id).first() is not None:
        raise ValueError("Группа с таким slug уже существует.")

    group.name = name
    group.slug = slug
    group.active = form.active.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Группа с таким названием или slug уже существует.")
    return group


def delete_user_group(group_id: int) -> None:
    """Удаляет группу, если к ней не привязаны пользователи."""
    group: UserGroup | None = db.session.get(UserGroup, group_id)
    if group is None:
        raise LookupError("Группа не найдена.")

    if User.query.filter_by(group_id=group_id).first() is not None:
        raise ValueError("Нельзя удалить группу, к которой привязаны пользователи.")

    db.session.delete(group)
    db.session.commit()