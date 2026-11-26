"""Генерация отчётов в формате xlsx."""

import os
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from decimal import Decimal

from app.extensions import db
from app.modules.catalog.models import Product, ProductMarketplace
from app.modules.catalog.pricing import get_exchange_rate
from app.modules.catalog.values import as_decimal
from app.modules.reports.registry import ReportDefinition, register_report


REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "instance", "reports"
)


def _ensure_reports_dir() -> str:
    """Создаёт папку для отчётов, если её нет."""
    path = os.path.abspath(REPORTS_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def generate_catalog_report(filters: dict) -> str:
    """Генерирует xlsx-отчёт по каталогу товаров.

    Возвращает путь к созданному файлу.
    """
    from app.modules.catalog.models import Marketplace

    category_id = filters.get("category_id")
    marketplace_id = filters.get("marketplace_id")

    query = Product.query
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if marketplace_id:
        query = query.filter(Product.marketplace_links.any(ProductMarketplace.marketplace_id == marketplace_id))

    products = query.order_by(Product.id).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Товары"

    headers = [
        "ID", "SKU", "Название", "Категория",
        "Цена входа, $", "Цена продажи, $",
        "Комиссия FBS мин, ₽", "Комиссия FBS макс, ₽",
        "Наценка мин, $", "Наценка макс, $",
        "Наценка мин, %", "Наценка макс, %",
        "Эквайринг, %", "Логистика мин, ₽", "Логистика макс, ₽", "Процент продажи",
        "Курс, ₽/$",
        "СПБ ТП", "МСК", "СПБ ОША", "СПБ СВХ", "СПБ БШО",
        "FBS Ozon", "Размещения",
        "Новая цена, $", "Новая цена, ₽",
        "Новая комиссия мин, ₽", "Новая комиссия макс, ₽",
        "Новая комиссия мин, %", "Новая комиссия макс, %",
        "Новая наценка, $",
    ]

    # Заголовок
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    rate = get_exchange_rate()

    for row_idx, product in enumerate(products, 2):
        # Находим ozon-связь
        ozon_link = None
        for link in product.marketplace_links:
            if link.marketplace and link.marketplace.marketplace_type == "Озон" and link.ozon_data:
                if ozon_link is None or (link.status == "v" and ozon_link.status != "v"):
                    ozon_link = link

        if ozon_link is None:
            # Товар без данных Ozon — записываем без комиссий
            placements = ", ".join(
                f"{link.marketplace.short_name or link.marketplace.name}: {link.status}"
                for link in product.marketplace_links
                if link.marketplace
            )
            values = [
                product.id,
                product.sku or "",
                product.name,
                product.category.name if product.category else "",
                float(product.cost_price) if product.cost_price is not None else None,
                float(product.selling_price) if product.selling_price is not None else None,
                None, None, None, None, None, None,
                None, None, None, None, None,
                product.stock_spb_tp,
                product.stock_msk,
                product.stock_spb_osh,
                product.stock_spb_svh,
                product.stock_spb_bsho,
                None,
                placements,
            ]
            for col, value in enumerate(values, 1):
                ws.cell(row=row_idx, column=col, value=value)
            continue

        acquiring_percent = ozon_link.marketplace.acquiring_percent
        if acquiring_percent is None:
            price = as_decimal((ozon_link.ozon_data.get("price") or {}).get("price"))
            if acquiring is not None and price and price != 0:
                acquiring_percent = (acquiring / price).quantize(Decimal("0.0001"))
                ozon_link.marketplace.acquiring_percent = acquiring_percent
                db.session.commit()
            else:
                raise ValueError(
                    f"Для магазина «{ozon_link.marketplace.name}» не задан процент эквайринга. "
                    "Импортируйте цены из Ozon."
                )

        ozon_data = ozon_link.ozon_data or {}
        commissions = ozon_data.get("commissions") or {}
        percent = as_decimal(commissions.get("sales_percent_fbs"))
        acquiring = as_decimal(ozon_data.get("acquiring"))
        if percent is None:
            raise ValueError(f"Товар {product.id}: нет процента продажи в данных Ozon.")
        percent = percent / Decimal(100)

        min_logistics = None
        max_logistics = None
        from app.modules.catalog.commission import _sum_commissions

        min_logistics = _sum_commissions(ozon_link.ozon_data, ("fbs_first_mile_min_amount", "fbs_direct_flow_trans_min_amount", "fbs_deliv_to_customer_amount"))
        max_logistics = _sum_commissions(ozon_link.ozon_data, ("fbs_first_mile_max_amount", "fbs_direct_flow_trans_max_amount", "fbs_deliv_to_customer_amount"))
        if min_logistics is None or max_logistics is None:
            raise ValueError(f"Товар {product.id}: нет данных логистики в Ozon.")

        placements = ", ".join(
            f"{link.marketplace.short_name or link.marketplace.name}: {link.status}"
            for link in product.marketplace_links
            if link.marketplace
        )

        values = [
            product.id,
            product.sku or "",
            product.name,
            product.category.name if product.category else "",
            float(product.cost_price) if product.cost_price is not None else None,
            float(product.selling_price) if product.selling_price is not None else None,
            float(ozon_link.fbs_commission_min) if ozon_link.fbs_commission_min is not None else None,
            float(ozon_link.fbs_commission_max) if ozon_link.fbs_commission_max is not None else None,
            float(ozon_link.markup_min_usd) if ozon_link.markup_min_usd is not None else None,
            float(ozon_link.markup_max_usd) if ozon_link.markup_max_usd is not None else None,
            float(ozon_link.markup_min_percent) if ozon_link.markup_min_percent is not None else None,
            float(ozon_link.markup_max_percent) if ozon_link.markup_max_percent is not None else None,
            float(acquiring_percent),
            float(min_logistics),
            float(max_logistics),
            float(percent),
            float(rate) if rate else None,
            product.stock_spb_tp,
            product.stock_msk,
            product.stock_spb_osh,
            product.stock_spb_svh,
            product.stock_spb_bsho,
            ozon_link.ozon_fbs_stock if ozon_link.ozon_fbs_stock is not None else None,
            placements,
        ]

        for col, value in enumerate(values, 1):
            ws.cell(row=row_idx, column=col, value=value)

        # Формулы для новых колонок
        # Y=25: Новая цена, $
        # Z=26: Новая цена, ₽ = Y*Q (Q=курс, col17)
        # AA=27: Новая комиссия мин, ₽ = Z*M + Z*P + N (M=эквайринг % col13, P=процент col16, N=логистика мин col14)
        # AB=28: Новая комиссия макс, ₽ = Z*M + Z*P + O (O=логистика макс col15)
        # AC=29: Новая комиссия мин, % = AA/Z*100
        # AD=30: Новая комиссия макс, % = AB/Z*100
        # AE=31: Новая наценка, $ = Y - E - AB/Q (новая цена $ - цена входа $ - новая комиссия макс в $)
        ws.cell(row=row_idx, column=26, value=f"=Y{row_idx}*Q{row_idx}")
        ws.cell(row=row_idx, column=27, value=f"=Z{row_idx}*M{row_idx}+Z{row_idx}*P{row_idx}+N{row_idx}")
        ws.cell(row=row_idx, column=28, value=f"=Z{row_idx}*M{row_idx}+Z{row_idx}*P{row_idx}+O{row_idx}")
        ws.cell(row=row_idx, column=29, value=f"=AA{row_idx}/Z{row_idx}*100")
        ws.cell(row=row_idx, column=30, value=f"=AB{row_idx}/Z{row_idx}*100")
        ws.cell(row=row_idx, column=31, value=f"=Y{row_idx}-E{row_idx}-AB{row_idx}/Q{row_idx}")

    # Автоширина колонок
    for col in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 16

    reports_dir = _ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_catalog_{timestamp}.xlsx"
    file_path = os.path.join(reports_dir, filename)
    wb.save(file_path)
    return file_path


# Регистрация отчёта
register_report(
    ReportDefinition(
        key="catalog",
        title="Выгрузка каталога",
        description="Полная выгрузка товаров с ценами, комиссиями, остатками и размещениями.",
        generator=generate_catalog_report,
    )
)