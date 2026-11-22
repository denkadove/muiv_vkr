"""Общий контракт клиентов API маркетплейсов."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketplaceCredentials:
    """Учётные данные для запросов к API маркетплейса."""

    client_id: str
    api_key: str


class MarketplaceApiError(Exception):
    """Ошибка запроса к API маркетплейса (понятная пользователю)."""


class MarketplaceClient(ABC):
    """Клиент, который умеет получать данные по артикулам товаров."""

    @abstractmethod
    def fetch_items(
        self,
        offer_ids: list[str],
        credentials: MarketplaceCredentials,
    ) -> dict[str, dict]:
        """Возвращает словарь ``offer_id -> item`` с данными из API."""
