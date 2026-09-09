import asyncio
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

import exchange_calendars as xcals
import pandas as pd

from .dataprovider import Dataprovider


Query = Tuple[str, datetime, datetime]

Query = Tuple[str, datetime, datetime]


class Aggregator:
    """Singleton queue and worker for data-provider queries."""

    _instance: Optional["Aggregator"] = None

    @staticmethod
    def _validate_settings(settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if settings is None:
            settings = {}
        if not isinstance(settings, dict):
            raise TypeError("settings must be a dictionary")

        provider_settings = settings.get("dataprovider", {})

        if not isinstance(provider_settings, dict):
            raise TypeError("settings['dataprovider'] must be a dictionary")

        batch_size = max(1, int(provider_settings.get("batch_size", 1)))
        time_interval = max(1, int(provider_settings.get("time_interval", 1)))
        max_query_size = max(1, int(provider_settings.get("max_query_size", 5000)))
        exchange_calendar = str(provider_settings.get("exchange_calendar", "XNYS"))
        endpoint = provider_settings.get("endpoint")
        api_key_b64 = provider_settings.get("api_key_b64")

        if not endpoint:
            raise ValueError("settings['dataprovider']['endpoint'] is required")
        if not api_key_b64:
            raise ValueError("settings['dataprovider']['api_key_b64'] is required")
        try:
            xcals.get_calendar(exchange_calendar)
        except Exception as error:
            raise ValueError(f"unknown exchange calendar: {exchange_calendar}") from error

        return {
            "dataprovider": {
                "batch_size": batch_size,
                "time_interval": time_interval,
                "max_query_size": max_query_size,
                "exchange_calendar": exchange_calendar,
                "endpoint": endpoint,
                "api_key_b64": api_key_b64,
            },
        }

    def __new__(cls, settings: Optional[Dict[str, Any]] = None, callback: Optional[Callable[[Any], None]] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Optional[Dict[str, Any]] = None, callback: Optional[Callable[[Any], None]] = None):
        if getattr(self, "_initialized", False):
            if callback is not None:
                self.callback = callback
            if settings is not None:
                self.settings = self._validate_settings(settings)
                self.batch_size = self.settings["dataprovider"]["batch_size"]
                self.provider_interval = self.settings["dataprovider"]["time_interval"]
                self.max_query_size = self.settings["dataprovider"]["max_query_size"]
                self.exchange_calendar = xcals.get_calendar(self.settings["dataprovider"]["exchange_calendar"])
                self.provider_config = self.settings["dataprovider"]
            return

        self.settings = self._validate_settings(settings)
        self.callback = callback or (lambda item: None)
        self.queue: Deque[Query] = deque()
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._initialized = True
        self.batch_size = self.settings["dataprovider"]["batch_size"]
        self.provider_interval = self.settings["dataprovider"]["time_interval"]
        self.max_query_size = self.settings["dataprovider"]["max_query_size"]
        self.exchange_calendar = xcals.get_calendar(self.settings["dataprovider"]["exchange_calendar"])
        self.provider_config = self.settings["dataprovider"]

    def handle_query(self, query: Query) -> List[Query]:
        """Queue a symbol/date range and return the individual intervals to fetch."""
        symbol, start_date, end_date = self._normalize_query(query)
        intervals = self.split_query((symbol, start_date, end_date))
        self.queue.extend(intervals)
        self.start_worker()
        return list(intervals)

    @staticmethod
    def _normalize_query(query: Query) -> Query:
        if not isinstance(query, tuple) or len(query) != 3:
            raise ValueError("query must be a tuple of (symbol, start_date, end_date)")

        symbol, start_date, end_date = query
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("query symbol must be a non-empty string")
        if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
            raise TypeError("query dates must be datetime instances")
        if end_date <= start_date:
            raise ValueError("query end_date must be greater than start_date")

        return symbol, start_date, end_date

    def split_query(self, query: Query) -> List[Query]:
        """Split a query into provider-compatible chunks, each under the API limit."""
        symbol, start_date, end_date = self._normalize_query(query)

        start_bound = pd.Timestamp(start_date)
        end_bound = pd.Timestamp(end_date)
        preserve_naive = start_bound.tzinfo is None
        if preserve_naive:
            start_bound = start_bound.tz_localize("UTC")
            end_bound = end_bound.tz_localize("UTC")
        else:
            start_bound = start_bound.tz_convert("UTC")
            end_bound = end_bound.tz_convert("UTC")

        trading_minutes = self.exchange_calendar.sessions_minutes(
            start_bound.date(), end_bound.date()
        )
        trading_minutes = trading_minutes[
            (trading_minutes >= start_bound) & (trading_minutes < end_bound)
        ]
        if not len(trading_minutes):
            return [(symbol, start_date, end_date)]

        max_points_per_chunk = max(1, self.max_query_size - 1)
        trading_minutes_per_chunk = max_points_per_chunk * self.provider_interval

        def to_datetime(value: pd.Timestamp) -> datetime:
            result = value.to_pydatetime()
            return result.replace(tzinfo=None) if preserve_naive else result

        intervals: List[Query] = []
        current_start = start_date
        for chunk_start in range(0, len(trading_minutes), trading_minutes_per_chunk):
            chunk_end = min(chunk_start + trading_minutes_per_chunk, len(trading_minutes))
            if chunk_end == len(trading_minutes):
                current_end = end_date
            else:
                current_end = to_datetime(
                    trading_minutes[chunk_end - 1] + pd.Timedelta(minutes=1)
                )
            intervals.append((symbol, current_start, current_end))
            current_start = current_end

        return intervals

    async def consume_batch(self) -> List[Any]:
        """Process up to batch_size queued queries and invoke the callback for each interval."""
        batch_size = min(self.batch_size, len(self.queue))
        if batch_size <= 0:
            return []

        queued_queries: List[Query] = []
        for _ in range(batch_size):
            if not self.queue:
                break
            queued_queries.append(self.queue.popleft())

        if not queued_queries:
            return []

        async def _fetch_payload(query: Query) -> Any:
            symbol, start_date, end_date = query
            try:
                provider = Dataprovider(symbol, start_date, end_date, self.provider_config)
                await provider.wait()

                response_error = provider.response()
                data = provider.result()

                if response_error is not None or data is None:
                    self.queue.appendleft(query)
                    return None
                return data
            except Exception:
                self.queue.appendleft(query)
                return None

        payloads = await asyncio.gather(*(_fetch_payload(query) for query in queued_queries))

        for payload in payloads:
            if payload is not None:
                self.callback(payload)

        return payloads

    def start_worker(self, interval_seconds: int = 60) -> Optional[asyncio.Task[None]]:
        """Start the minute-based worker once per singleton instance."""
        if self._worker_task is not None and not self._worker_task.done():
            return self._worker_task

        async def _worker_loop() -> None:
            while True:
                await asyncio.sleep(interval_seconds)
                await self.consume_batch()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None

        self._worker_task = loop.create_task(_worker_loop())
        return self._worker_task
