"""Приведение значений, приходящих из ответов API маркетплейсов."""

from decimal import Decimal, InvalidOperation


def as_decimal(value) -> Decimal | None:
    """Преобразует число из API/БД в Decimal или возвращает None."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None
