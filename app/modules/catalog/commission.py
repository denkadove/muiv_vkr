"""Расчёт минимальной и максимальной итоговой комиссии FBS."""

from decimal import Decimal, ROUND_HALF_UP

from app.modules.catalog.values import as_decimal

CENT = Decimal("0.01")

# Фиксированные суммы из ответа /v5/product/info/prices, ₽.
FBS_MIN_FIELDS = (
    "fbs_first_mile_min_amount",
    "fbs_direct_flow_trans_min_amount",
    "fbs_deliv_to_customer_amount",
)
FBS_MAX_FIELDS = (
    "fbs_first_mile_max_amount",
    "fbs_direct_flow_trans_max_amount",
    "fbs_deliv_to_customer_amount",
)


def _sum_commissions(ozon_data: dict | None, fields: tuple[str, ...]) -> Decimal | None:
    commissions = (ozon_data or {}).get("commissions") or {}
    total = Decimal(0)
    for field in fields:
        value = as_decimal(commissions.get(field))
        if value is None:
            return None
        total += value
    return total


def calculate_fbs_commissions(
    ozon_data: dict | None,
    selling_price,
    commission_fbs,
) -> tuple[Decimal | None, Decimal | None]:
    """Возвращает (минимум, максимум) комиссии FBS в рублях.

    Минимум и максимум различаются только полями логистики; процент продажи
    берётся из хранимой доли (0.51 для 51%). Если не хватает хотя бы одного
    слагаемого, возвращается (None, None).
    """
    acquiring = as_decimal((ozon_data or {}).get("acquiring"))
    price = as_decimal(selling_price)
    percent = as_decimal(commission_fbs)
    min_logistics = _sum_commissions(ozon_data, FBS_MIN_FIELDS)
    max_logistics = _sum_commissions(ozon_data, FBS_MAX_FIELDS)

    if any(value is None for value in (
        acquiring, price, percent, min_logistics, max_logistics
    )):
        return None, None

    percent_amount = price * percent
    return (
        (acquiring + percent_amount + min_logistics).quantize(CENT, rounding=ROUND_HALF_UP),
        (acquiring + percent_amount + max_logistics).quantize(CENT, rounding=ROUND_HALF_UP),
    )
