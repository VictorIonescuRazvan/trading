import asyncio
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple

from .dataprovider import Dataprovider


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
        endpoint = provider_settings.get("endpoint")
        api_key_b64 = provider_settings.get("api_key_b64")

        if not endpoint:
            raise ValueError("settings['dataprovider']['endpoint'] is required")
        if not api_key_b64:
            raise ValueError("settings['dataprovider']['api_key_b64'] is required")

        return {
            "dataprovider": {
                "batch_size": batch_size,
                "time_interval": time_interval,
                "max_query_size": max_query_size,
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
                self.provider_config = self.settings["dataprovider"]
            return

        self.settings = self._validate_settings(settings)
        self.callback = callback or (lambda item: None)
        self.queue: Deque[Query] = deque()
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._initialized = True
        self.batch_size = self.settings["dataprovider"]["batch_size"]
        self.provider_interval = self.settings["dataprovider"]["time_interval"]
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

        max_requested_points = 5000
        max_points_per_chunk = max_requested_points - 1
        chunk_span = max_points_per_chunk * self.provider_interval * 60
        chunk_delta = timedelta(seconds=chunk_span)

        intervals: List[Query] = []
        current_start = start_date

        while current_start < end_date:
            current_end = min(current_start + chunk_delta, end_date)
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
