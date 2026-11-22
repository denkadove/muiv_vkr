"""Реестр клиентов API маркетплейсов."""

from app.modules.catalog.integrations.base import (
    MarketplaceApiError,
    MarketplaceClient,
    MarketplaceCredentials,
)
from app.modules.catalog.integrations.ozon import (
    OZON_MARKETPLACE_TYPE,
    OzonClient,
)

CLIENTS: dict[str, type[MarketplaceClient]] = {
    OZON_MARKETPLACE_TYPE: OzonClient,
}


def get_client(marketplace_type: str) -> MarketplaceClient | None:
    """Возвращает клиента для типа маркетплейса или None, если его нет."""
    client_class = CLIENTS.get(marketplace_type)
    return client_class() if client_class is not None else None


__all__ = [
    "CLIENTS",
    "OZON_MARKETPLACE_TYPE",
    "MarketplaceApiError",
    "MarketplaceClient",
    "MarketplaceCredentials",
    "OzonClient",
    "get_client",
]
