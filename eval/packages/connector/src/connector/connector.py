from __future__ import annotations

from typing import Any

import httpx


class TickerplantConnector:
    """Thin client for the Tickerplant FastAPI endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        client: httpx.Client | Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") or "http://localhost:8000"
        self.client = client if client is not None else httpx.Client(base_url=self.base_url)

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        request = getattr(self.client, "request", None)
        if request is None:
            raise TypeError("Client must implement a request(method, url, **kwargs) method")
        response = request(method, path, **kwargs)
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        return response

    def meta(self, symbol: str, start: str, end: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            "/meta",
            params={"symbol": symbol, "start": start, "end": end},
        )
        return response.json()

    def data(self, data: dict[str, list[dict[str, Any]]]) -> None:
        response = self._request("POST", "/data", json={"data": data})
        if getattr(response, "status_code", None) == 204:
            return None
        return None

    def setdone(self, symbol: str, year: int, month: int) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/setdone",
            json={"symbol": symbol, "year": year, "month": month},
        )
        return response.json()


__all__ = ["TickerplantConnector"]
