"""Сервисный слой: бизнес-логика, независимая от HTTP."""

from sqlalchemy.exc import IntegrityError

from app import bcrypt, db
from app.forms import (
    CategoryForm,
    CreateUserForm,
    ProductForm,
    RegisterForm,
    UserEditForm,
    MarketplaceForm,
)
from app.models import (
    ADMIN_GROUP_ID,
    DEFAULT_CATEGORY_NAME,
    USER_GROUP_ID,
    Category,
    Product,
    User,
    Marketplace
)


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


def create_user(
    form: RegisterForm | CreateUserForm,
    group_id: int | None = None,
    active: bool = True,
    ) -> User:
    """Создаёт пользователя: служит и для регистрации, и для админ-панели.

    Особенности:
        - без group_id первый пользователь системы получает группу
          администратора, остальные — группу пользователя;
        - пароль сохраняется только в виде bcrypt-хэша.

    Аргументы:
        form (RegisterForm | CreateUserForm): форма с логином, email и паролем.
        group_id (int | None): группа пользователя; None — определить
        по счётчику пользователей.
        active (bool): признак активности учётной записи.

    Возвращает:
        User: созданный пользователь, сохранённый в базе.

    Исключения:
        ValueError: логин или email уже заняты.
    """
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
    # Проверка уникальности не атомарна: дубликат ловим по ограничению БД
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Пользователь с таким логином или email уже существует.")
    return user


def update_user(user_id: int, form: UserEditForm) -> User:
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


def get_categories() -> list[Category]:
    """Возвращает список категорий в порядке создания.

    Особенности:
        - при пустой таблице создаёт категорию по умолчанию
          «Без категории» (ленивый сидинг).

    Возвращает:
        list[Category]: все категории, по умолчанию — первой.
    """
    # TODO: временный ленивый сидинг — на финальном этапе заменить на
    # явную инициализацию БД
    if Category.query.count() == 0:
        db.session.add(Category(name=DEFAULT_CATEGORY_NAME))
        db.session.commit()
    return Category.query.order_by(Category.id).all()


def create_category(form: CategoryForm) -> Category:
    """Создаёт категорию.

    Аргументы:
        form (CategoryForm): провалидированная форма категории.

    Возвращает:
        Category: созданная категория.

    Исключения:
        ValueError: категория с таким названием уже существует.
    """
    if Category.query.filter_by(name=form.name.data).first() is not None:
        raise ValueError("Категория с таким названием уже существует.")

    category = Category(name=form.name.data)
    db.session.add(category)
    # Проверка уникальности не атомарна: дубликат ловим по ограничению БД
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Категория с таким названием уже существует.")
    return category


def update_category(category_id: int, form: CategoryForm) -> Category:
    """Переименовывает категорию.

    Особенности:
        - категорию по умолчанию «Без категории» переименовывать нельзя.

    Аргументы:
        category_id (int): идентификатор категории.
        form (CategoryForm): провалидированная форма категории.

    Возвращает:
        Category: обновлённая категория.

    Исключения:
        LookupError: категория не найдена.
        ValueError: попытка переименовать категорию по умолчанию
        или дубликат названия.
    """
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        raise LookupError("Категория не найдена.")
    if category.name == DEFAULT_CATEGORY_NAME:
        raise ValueError("Нельзя переименовать категорию «Без категории».")
    if (
        Category.query.filter(Category.name == form.name.data, Category.id != category_id)
        .first()
        is not None
    ):
        raise ValueError("Категория с таким названием уже существует.")

    category.name = form.name.data
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("Категория с таким названием уже существует.")
    return category


def delete_category(category_id: int) -> None:
    """Удаляет категорию, перенося её товары в «Без категории».

    Особенности:
        - категорию по умолчанию удалить нельзя.

    Аргументы:
        category_id (int): идентификатор категории.

    Исключения:
        LookupError: категория не найдена.
        ValueError: попытка удалить категорию по умолчанию.
    """
    category: Category | None = db.session.get(Category, category_id)
    if category is None:
        raise LookupError("Категория не найдена.")
    if category.name == DEFAULT_CATEGORY_NAME:
        raise ValueError("Нельзя удалить категорию «Без категории».")

    default_category: Category | None = Category.query.filter_by(
        name=DEFAULT_CATEGORY_NAME
    ).first()
    if default_category is None:
        default_category = Category(name=DEFAULT_CATEGORY_NAME)
        db.session.add(default_category)
        db.session.flush()  # flush: id нужен до commit

    Product.query.filter_by(category_id=category_id).update(
        {"category_id": default_category.id}
    )
    db.session.delete(category)
    db.session.commit()


def get_marketplaces_list() -> list[str]:
    """Получает список маркетплейсов из БД.

    Возвращает:
        list[str]: список названий маркетплейсов.
    """
    marketplaces = Marketplace.query.order_by(Marketplace.name).all()
    return [mp.name for mp in marketplaces]


def create_product(form: ProductForm) -> Product:
    """Создаёт товар.

    Аргументы:
        form (ProductForm): провалидированная форма товара.

    Возвращает:
        Product: созданный товар.

    Исключения:
        ValueError: указанная категория не существует.
    """
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    marketplaces: Marketplace = Marketplace.query.filter(Marketplace.id.in_(form.marketplaces.data or [])).all()

    product = Product(
        name=form.name.data,
        price=form.price.data,
        marketplaces=marketplaces,
        description=form.description.data,
        category_id=category.id,
    )
    db.session.add(product)
    db.session.commit()
    return product


def update_product(product_id: int, form: ProductForm) -> Product:
    """Обновляет товар.

    Аргументы:
        product_id (int): идентификатор товара.
        form (ProductForm): провалидированная форма товара.

    Возвращает:
        Product: обновлённый товар.

    Исключения:
        LookupError: товар не найден.
        ValueError: указанная категория не существует.
    """
    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    category: Category | None = db.session.get(Category, form.category_id.data)
    if category is None:
        raise ValueError("Указанная категория не существует.")

    # Получаем объекты маркетплейсов по ID
    marketplaces: Marketplace = Marketplace.query.filter(Marketplace.id.in_(form.marketplaces.data or [])).all()

    product.name = form.name.data
    product.price = form.price.data
    product.description = form.description.data
    product.category_id = category.id
    product.marketplaces = marketplaces
    db.session.commit()
    return product


def delete_product(product_id: int) -> None:
    """Удаляет товар.

    Аргументы:
        product_id (int): идентификатор товара.

    Исключения:
        LookupError: товар не найден.
    """
    product: Product | None = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Товар не найден.")
    db.session.delete(product)
    db.session.commit()


def create_marketplace(form: MarketplaceForm) -> Marketplace:
    """Создаёт маркетплейс.

    Аргументы:
        form (MarketplaceForm): провалидированная форма маркетплейса.

    Возвращает:
        Marketplace: созданный маркетплейс.

    """

    marketplace = Marketplace(
        name=form.name.data,
        api_key=form.api_key.data,
        description=form.description.data,
    )
    db.session.add(marketplace)
    db.session.commit()
    return marketplace

def update_marketplace(marketplace_id: int, form: MarketplaceForm) -> Marketplace:
    """Обновляет маркетплейс.

    Аргументы:
        marketplace_id (int): идентификатор маркетплейса.
        form (MarketplaceForm): провалидированная форма маркетплейса.

    Возвращает:
        Marketplace: обновлённый маркетплейса.

    Исключения:
        LookupError: маркетплейс не найден.
    """
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        raise LookupError("Маркетплейс не найден.")

    marketplace.name = form.name.data
    marketplace.api_key= form.api_key.data
    marketplace.description = form.description.data
    db.session.commit()
    return marketplace

def delete_marketplace(marketplace_id: int) -> None:
    """Удаляет маркетплейс.

    Аргументы:
        marketplace_id (int): идентификатор маркетплейса.

    Исключения:
        LookupError: маркетплейса не найден.
    """
    marketplace: Marketplace | None = db.session.get(Marketplace, marketplace_id)
    if marketplace is None:
        raise LookupError("Маркетплейс не найден.")

    db.session.delete(marketplace)
    db.session.commit()