"""Скрипт заполнения БД товарами из файла товары.xlsx.

Запуск из корня проекта:
    python seed_products.py
    python seed_products.py --xlsx путь/к/файлу.xlsx
    python seed_products.py --db muiv_vkr/instance/site.db

Файл товары.xlsx должен лежать в папке проекта (на уровень выше приложения).
"""

import argparse
import os
import sys
from typing import Optional

# Путь к приложению
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(PROJECT_DIR, "muiv_vkr")
sys.path.insert(0, APP_DIR)

from openpyxl import load_workbook

from app import create_app
from app.extensions import db
from app.modules.catalog.models import (
    Category,
    Marketplace,
    Primitive,
    Product,
    ProductMarketplace,
    ProductImage,
    product_primitives,
)

DEFAULT_XLSX = os.path.join(PROJECT_DIR, "товары.xlsx")
DEFAULT_DB = os.path.join(APP_DIR, "instance", "site.db")

# Магазины: (имя, тип, short_name)
SHOPS: list[tuple[str, str, str]] = [
    ("Яндекс ПШТ", "Яндекс", "Я_ПШТ"),
    ("Озон ПШТ", "Озон", "О_ПШТ"),
    ("ВБ ПШТ", "ВБ", "WB_ПШТ"),
    ("Яндекс Соловьев", "Яндекс", "Я_Сол"),
    ("Озон Соловьев", "Озон", "О_Сол"),
    ("ВБ Соловьев", "ВБ", "WB_Сол"),
]

# Соответствие колонок файла магазинам
SHOP_COLUMNS: dict[str, int] = {
    "Я_ПШТ": 6,
    "О_ПШТ": 7,
    "WB_ПШТ": 8,
    "Я_Сол": 9,
    "О_Сол": 10,
    "WB_Сол": 11,
}


def get_or_create_shop(name: str, mtype: str, short_name: str) -> Marketplace:
    """Возвращает существующий или создаёт новый маркетплейс."""
    shop = Marketplace.query.filter_by(name=name).first()
    if shop is None:
        shop = Marketplace(
            name=name,
            marketplace_type=mtype,
            short_name=short_name,
        )
        db.session.add(shop)
        db.session.flush()
    else:
        shop.marketplace_type = mtype
        shop.short_name = short_name
    return shop


def get_or_create_category(name: Optional[str]) -> Category:
    """Возвращает существующую или создаёт новую категорию."""
    if not name:
        name = "Без категории"
    name = str(name).strip()
    category = Category.query.filter_by(name=name).first()
    if category is None:
        category = Category(name=name)
        db.session.add(category)
        db.session.flush()
    return category


def get_or_create_primitive(sku) -> Optional[Primitive]:
    """Возвращает существующий или создаёт новый примитив с ценой 0."""
    if not sku or str(sku).strip() in ("", "0", "-"):
        return None
    sku = str(sku).strip()
    primitive = Primitive.query.filter_by(sku=sku).first()
    if primitive is None:
        primitive = Primitive(
            sku=sku,
            name=sku,
            price=0,
        )
        db.session.add(primitive)
        db.session.flush()
    return primitive


def clean_db() -> None:
    """Очищает товары и связи (примитивы и категории не удаляем)."""
    db.session.execute(product_primitives.delete())
    ProductMarketplace.query.delete()
    ProductImage.query.delete()
    Product.query.delete()
    db.session.commit()


def seed(xlsx_path: str) -> None:
    """Основная функция заполнения БД."""
    if not os.path.exists(xlsx_path):
        print(f"Файл не найден: {xlsx_path}")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        try:
            db.create_all()
            clean_db()

            # Создаём магазины
            shops: dict[str, Marketplace] = {}
            for name, mtype, short_name in SHOPS:
                shop = get_or_create_shop(name, mtype, short_name)
                shops[short_name] = shop
            db.session.commit()

            wb = load_workbook(xlsx_path, data_only=True)
            ws = wb.active

            header = [cell.value for cell in ws[1]]
            idx_sku = header.index("кб")
            idx_name = header.index("Название")
            idx_price = header.index("фиксированная цена, USD")
            idx_cat = header.index("Категория")
            idx_prim = [header.index(f"Примитив {i}") for i in (1, 2, 3)]

            created_products = 0
            skipped = 0
            seen_skus: set[str] = set()

            for row in ws.iter_rows(min_row=2, values_only=True):
                sku = row[idx_sku]
                if not sku:
                    continue
                sku = str(sku).strip()
                if sku in ("", "-", "0") or sku in seen_skus:
                    skipped += 1
                    continue
                seen_skus.add(sku)

                name = row[idx_name] or sku
                price = row[idx_price]
                category_name = row[idx_cat]

                category = get_or_create_category(category_name)

                product = Product(
                    sku=sku,
                    name=str(name).strip(),
                    selling_price=price,
                    category_id=category.id,
                )
                db.session.add(product)
                db.session.flush()

                # Состав (дедупликация примитивов внутри товара)
                prim_qty: dict[int, int] = {}
                for pi in idx_prim:
                    prim_sku = row[pi]
                    primitive = get_or_create_primitive(prim_sku)
                    if primitive is not None:
                        prim_qty[primitive.id] = prim_qty.get(primitive.id, 0) + 1
                for prim_id, qty in prim_qty.items():
                    db.session.execute(
                        product_primitives.insert().values(
                            product_id=product.id,
                            primitive_id=prim_id,
                            quantity=qty,
                        )
                    )

                # Размещения
                for short_name, col_idx in SHOP_COLUMNS.items():
                    status = row[col_idx]
                    if status is None:
                        status = "x"
                    status = str(status).strip()
                    if status not in ("N", "o", "v", "x"):
                        status = "x"
                    shop = shops[short_name]
                    link = ProductMarketplace(
                        product_id=product.id,
                        marketplace_id=shop.id,
                        status=status,
                        external_offer_id=sku,
                    )
                    db.session.add(link)

                created_products += 1

                if created_products % 100 == 0:
                    db.session.commit()
                    print(f"Создано товаров: {created_products}")

            db.session.commit()
            print(f"Готово. Всего товаров: {created_products}, пропущено: {skipped}")

        except Exception as error:
            db.session.rollback()
            print(f"Ошибка: {error}")
            sys.exit(1)


def main() -> None:
    """Точка входа."""
    parser = argparse.ArgumentParser(description="Заполнение БД товарами из xlsx")
    parser.add_argument(
        "--xlsx",
        default=DEFAULT_XLSX,
        help="Путь к файлу товары.xlsx",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help="Путь к базе данных (переопределяет instance/site.db)",
    )
    args = parser.parse_args()

    # Переопределяем путь к БД через переменную окружения Flask
    db_path = os.path.abspath(args.db)
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    seed(args.xlsx)


if __name__ == "__main__":
    main()