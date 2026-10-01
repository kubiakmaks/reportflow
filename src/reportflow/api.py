from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Iterator

import requests


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    token: str
    page_size: int = 25
    timeout_seconds: float = 5.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.15


class OrdersApiClient:
    def __init__(self, config: ApiConfig, logger: logging.Logger | None = None) -> None:
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def _get_json(self, path: str, query: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = requests.get(
                    url,
                    params=query,
                    headers={"Authorization": f"Bearer {self.config.token}"},
                    timeout=self.config.timeout_seconds,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt == self.config.max_retries:
                        response.raise_for_status()
                    self.logger.warning("Retryable HTTP %s on attempt %s", response.status_code, attempt)
                else:
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise RuntimeError("API response is not an object")
                    return payload
            except requests.RequestException as exc:
                if attempt == self.config.max_retries:
                    raise RuntimeError(f"API request failed: {url}") from exc
                self.logger.warning("Network error on attempt %s: %s", attempt, exc)
            time.sleep(self.config.retry_backoff_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("unreachable retry state")

    def iter_pages(self) -> Iterator[tuple[int, list[dict[str, Any]]]]:
        page = 1
        while True:
            payload = self._get_json("v1/orders", {"page": page, "page_size": self.config.page_size})
            records = payload.get("items")
            if not isinstance(records, list):
                raise RuntimeError("API response does not contain an items list")
            yield page, records
            if not payload.get("next_page"):
                break
            page = int(payload["next_page"])
