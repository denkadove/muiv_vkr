"""Курс доллара и конвертация цен для отображения."""

from decimal import Decimal, ROUND_HALF_UP

from flask import g

from app.modules.settings.services import get_float_setting

CENT = Decimal("0.01")
EXCHANGE_RATE_SETTING = "dollar_exchange_rate"


def get_exchange_rate() -> Decimal | None:
    """Возвращает курс доллара; кэширует его на время запроса."""
    if hasattr(g, "exchange_rate"):
        return g.exchange_rate

    value = get_float_setting(EXCHANGE_RATE_SETTING)
    rate = Decimal(str(value)) if value is not None and value > 0 else None
    g.exchange_rate = rate
    return rate


def usd_to_rub(usd, rate: Decimal | None) -> Decimal | None:
    """Переводит доллары в рубли по курсу."""
    if usd is None or rate is None:
        return None
    return (Decimal(str(usd)) * rate).quantize(CENT, rounding=ROUND_HALF_UP)


def rub_to_usd(rub, rate: Decimal | None) -> Decimal | None:
    """Переводит рубли в доллары по курсу."""
    if rub is None or rate is None:
        return None
    return (Decimal(str(rub)) / rate).quantize(CENT, rounding=ROUND_HALF_UP)
