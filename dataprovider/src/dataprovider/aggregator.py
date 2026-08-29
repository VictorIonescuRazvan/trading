import asyncio
from datetime import datetime
from typing import Any

from .dataprovider import Dataprovider

MAX_RANGE_MINUTES = 5000


class Aggregator:
    """Coordinate one or more Dataprovider requests for a symbol/date-range query."""

    def __init__(self, settings: dict[str, Any], query: dict[str, dict[str, datetime]]):
        self.settings = settings or {}
        self.query = query or {}
        self.app_config = self.settings.get("app", {})
        self.dataprovider_config = self.settings.get("dataprovider", {})
        if not isinstance(self.app_config, dict) or not isinstance(self.dataprovider_config, dict):
            raise ValueError("settings must contain 'app' and 'dataprovider' mappings")

    async def aggregate(self) -> tuple[dict[str, Any], list[str]]:
        if not self.query:
            return {}, []

        dataproviders = []
        for symbol, bounds in self.query.items():
            if not isinstance(bounds, dict):
                raise ValueError(f"query entry for '{symbol}' must contain start_date and end_date")
            start_date = bounds.get("start_date")
            end_date = bounds.get("end_date")
            if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
                raise ValueError(
                    f"query entry for '{symbol}' must contain valid datetime values for start_date and end_date"
                )
            elapsed_minutes = (end_date - start_date).total_seconds() / 60
            if elapsed_minutes > MAX_RANGE_MINUTES:
                raise ValueError(
                    f"query entry for '{symbol}' exceeds the maximum allowed range of {MAX_RANGE_MINUTES} minutes"
                )
            dataproviders.append(
                Dataprovider(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    config={**self.dataprovider_config},
                )
            )

        await asyncio.gather(*(dataprovider.wait() for dataprovider in dataproviders))

        combined: dict[str, Any] = {}
        errors: list[str] = []
        for dataprovider in dataproviders:
            if dataprovider.response() is not None:
                errors.append(dataprovider.response() or "Unknown dataprovider error")
                continue
            result = dataprovider.result()
            if result is None:
                errors.append("Dataprovider returned no data")
                continue
            combined.update(result)

        return combined, errors
