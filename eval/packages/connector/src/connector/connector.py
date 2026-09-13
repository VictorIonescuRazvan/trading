from __future__ import annotations

from typing import Any
import logging

import httpx


request_logger = logging.getLogger("eval.connector")


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
        try:
            response = request(method, path, **kwargs)
        except Exception:
            request_logger.critical("tickerplant request failed method=%s path=%s", method, path)
            raise
        if hasattr(response, "raise_for_status"):
            try:
                response.raise_for_status()
            except Exception:
                request_logger.critical("tickerplant request failed method=%s path=%s", method, path)
                raise
        request_logger.info("tickerplant request succeeded method=%s path=%s", method, path)
        return response

    def meta(self, symbol: str, start: str, end: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            "/meta",
            params={"symbol": symbol, "start": start, "end": end},
        )
        return response.json()

    def getpending(self, start: str, end: str) -> list[dict[str, Any]]:
        response = self._request(
            "GET",
            "/getpending",
            params={"start": start, "end": end},
        )
        return response.json()

    def data(self, data: dict[str, list[dict[str, Any]]]) -> None:
        response = self._request("POST", "/data", json={"data": data})
        if getattr(response, "status_code", None) == 204:
            return None
        return None

    def getdata(
        self,
        start: str,
        end: str,
        symbols: list[str],
    ) -> list[dict[str, Any]]:
        response = self._request(
            "POST",
            "/getdata",
            json={"start": start, "end": end, "symbols": symbols},
        )
        return response.json()

    def setdone(self, symbol: str, year: int, month: int) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/setdone",
            json={"symbol": symbol, "year": year, "month": month},
        )
        return response.json()


__all__ = ["TickerplantConnector"]
