"""Импорт цен, комиссий и других данных из Ozon Seller API."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db
from app.modules.catalog.integrations import (
    OZON_MARKETPLACE_TYPE,
    MarketplaceApiError,
    MarketplaceCredentials,
    get_client,
)
from app.modules.catalog.models import Marketplace, ProductMarketplace
from app.modules.catalog.values import as_decimal

# Поля ответа commissions храним отдельными колонками: по ним удобно
# фильтровать и сортировать товары. Остальные поля остаются в ozon_data.
PERCENT_FIELDS = {
    "sales_percent_fbo": "commission_fbo",
    "sales_percent_fbs": "commission_fbs",
    "sales_percent_fbp": "commission_fbp",
    "sales_percent_rfbs": "commission_rfbs",
}
OFFER_CHUNK_SIZE = 1000


@dataclass
class ImportResult:
    """Счётчики импорта для отображения пользователю."""

    updated: int = 0
    not_found: int = 0
    failed: int = 0
    skipped: int = 0
    messages: list[str] = field(default_factory=list)

    def summary(self) -> str:
        text = (
            f"Обновлено: {self.updated}, не найдено: {self.not_found}, "
            f"ошибок: {self.failed}, пропущено: {self.skipped}."
        )
        if self.messages:
            text += " " + " ".join(self.messages[:5])
        return text


def _as_percent(value) -> Decimal | None:
    """Ozon возвращает проценты числом: 15 -> 0.15."""
    amount = as_decimal(value)
    return amount / Decimal(100) if amount is not None else None


def _as_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_item(link: ProductMarketplace, item: dict, now: datetime) -> None:
    """Сохраняет полный ответ Ozon и его ключевые поля в связь товара."""
    link.ozon_data = item
    link.ozon_product_id = _as_int(item.get("product_id"))
    link.ozon_price = as_decimal((item.get("price") or {}).get("price"))

    commissions = item.get("commissions") or {}
    for source, target in PERCENT_FIELDS.items():
        setattr(link, target, _as_percent(commissions.get(source)))

    link.ozon_updated_at = now
    link.ozon_error = None


def import_ozon_data(marketplace_id: int | None = None) -> ImportResult:
    """Обновляет данные товаров из Ozon для одного или всех магазинов.

    При ошибке API старые значения комиссий не затираются — пишется только
    текст ошибки в ``ozon_error``.
    """
    result = ImportResult()

    query = Marketplace.query.filter_by(marketplace_type=OZON_MARKETPLACE_TYPE)
    if marketplace_id is not None:
        query = query.filter(Marketplace.id == marketplace_id)
    marketplaces = query.order_by(Marketplace.id).all()

    if not marketplaces:
        result.messages.append("Магазинов типа «Озон» не найдено.")
        return result

    for marketplace in marketplaces:
        if not marketplace.client_id or not marketplace.api_key:
            result.skipped += 1
            result.messages.append(
                f"«{marketplace.name}»: не заполнены Client-Id или Api-Key."
            )
            continue

        client = get_client(marketplace.marketplace_type)
        if client is None:
            result.skipped += 1
            result.messages.append(
                f"«{marketplace.name}»: нет клиента для API этого типа."
            )
            continue

        links = ProductMarketplace.query.filter(
            ProductMarketplace.marketplace_id == marketplace.id,
            ProductMarketplace.external_offer_id.isnot(None),
            ProductMarketplace.external_offer_id != "",
        ).all()
        if not links:
            result.skipped += 1
            result.messages.append(
                f"«{marketplace.name}»: не заполнены offer_id у товаров."
            )
            continue

        by_offer: dict[str, list[ProductMarketplace]] = {}
        for link in links:
            offer_id = str(link.external_offer_id).strip()
            by_offer.setdefault(offer_id, []).append(link)
        offers = list(by_offer)

        credentials = MarketplaceCredentials(
            client_id=marketplace.client_id,
            api_key=marketplace.api_key,
        )
        for start in range(0, len(offers), OFFER_CHUNK_SIZE):
            chunk = offers[start:start + OFFER_CHUNK_SIZE]
            try:
                items = client.fetch_items(chunk, credentials)
            except MarketplaceApiError as error:
                result.failed += sum(len(by_offer[offer]) for offer in chunk)
                result.messages.append(f"«{marketplace.name}»: {error}")
                for offer in chunk:
                    for link in by_offer[offer]:
                        link.ozon_error = str(error)
                continue

            now = datetime.now(timezone.utc)
            for offer in chunk:
                item = items.get(offer)
                targets = by_offer[offer]
                if item is None:
                    for link in targets:
                        link.ozon_error = "Не найдено в Ozon"
                        result.not_found += 1
                    continue
                for link in targets:
                    _apply_item(link, item, now)
                    result.updated += 1

        try:
            db.session.commit()
        except Exception as error:
            db.session.rollback()
            result.failed += len(links)
            result.messages.append(f"«{marketplace.name}»: ошибка сохранения: {error}")

    return result
