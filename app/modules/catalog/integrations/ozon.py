"""Клиент Ozon Seller API: цены и комиссии по артикулам продавца."""

import time

import requests

from app.modules.catalog.integrations.base import (
    MarketplaceApiError,
    MarketplaceClient,
    MarketplaceCredentials,
)

OZON_MARKETPLACE_TYPE = "Озон"
OZON_PRICES_URL = "https://api-seller.ozon.ru/v5/product/info/prices"
OZON_PAGE_SIZE = 1000
REQUEST_TIMEOUT = 10
MAX_ATTEMPTS = 3

class OzonClient(MarketplaceClient):
    """Запрашивает /v5/product/info/prices пачками до 1000 offer_id."""

    def fetch_items(
        self,
        offer_ids: list[str],
        credentials: MarketplaceCredentials,
    ) -> dict[str, dict]:
        if not offer_ids:
            return {}

        headers = {
            "Client-Id": credentials.client_id,
            "Api-Key": credentials.api_key,
            "Content-Type": "application/json",
        }
        items: dict[str, dict] = {}
        cursor = ""
        seen_cursors: set[str] = set()

        while True:
            payload = {
                "filter": {"offer_id": list(offer_ids), "visibility": "ALL"},
                "limit": OZON_PAGE_SIZE,
                "cursor": cursor,
            }
            body = self._post(payload, headers)
            for item in body.get("items") or []:
                offer_id = item.get("offer_id")
                if offer_id is not None:
                    items[str(offer_id)] = item

            cursor = body.get("cursor") or ""
            if not cursor or cursor in seen_cursors:
                break
            seen_cursors.add(cursor)

        return items

    def _post(self, payload: dict, headers: dict[str, str]) -> dict:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = requests.post(
                    OZON_PRICES_URL,
                    json=payload,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except requests.RequestException as error:
                raise MarketplaceApiError(f"Ошибка запроса к Ozon: {error}") from error

            if response.status_code in (401, 403):
                raise MarketplaceApiError("Проверьте Client-Id и Api-Key Ozon.")
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < MAX_ATTEMPTS - 1:
                    time.sleep(0.5 * (2 ** attempt))
                    continue
                raise MarketplaceApiError(
                    f"Ozon не ответил после {MAX_ATTEMPTS} попыток "
                    f"(HTTP {response.status_code})."
                )
            if response.status_code >= 400:
                raise MarketplaceApiError(
                    f"Ozon вернул ошибку HTTP {response.status_code}: "
                    f"{response.text[:200]}"
                )

            try:
                body = response.json()
            except ValueError as error:
                raise MarketplaceApiError("Ozon вернул некорректный JSON.") from error
            if not isinstance(body, dict):
                raise MarketplaceApiError("Ozon вернул неожидаемый формат ответа.")
            return body

        raise MarketplaceApiError("Ozon не ответил после нескольких попыток.")
