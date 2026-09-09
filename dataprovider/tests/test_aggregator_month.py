import asyncio
import base64
from datetime import datetime
from pathlib import Path

from dataprovider.aggregator import Aggregator
from dataprovider import dataprovider as dataprovider_module


class FakeResponse:
    status = 200
    headers = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    async def json(self):
        return {"meta": {"symbol": "AAPL"}, "values": []}


class FakeSession:
    requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def get(self, endpoint, params, timeout):
        self.requests.append((endpoint, params, timeout))
        return FakeResponse()


def test_aggregator_fetches_full_may_2026_range_using_trading_minutes(monkeypatch, tmp_path: Path):
    log_path = tmp_path / "requests.log"
    monkeypatch.setattr(dataprovider_module, "REQUEST_LOG_PATH", log_path)
    monkeypatch.setattr(dataprovider_module.aiohttp, "ClientSession", FakeSession)
    FakeSession.requests = []
    Aggregator._instance = None

    config = {
        "dataprovider": {
            "batch_size": 8,
            "time_interval": 1,
            "max_query_size": 5000,
            "exchange_calendar": "XNYS",
            "endpoint": "https://example.test/time_series",
            "api_key_b64": base64.b64encode(b"test-key").decode(),
        }
    }
    aggregator = Aggregator(config)
    start = datetime(2026, 5, 1)
    end = datetime(2026, 6, 1)
    queued = aggregator.handle_query(("AAPL", start, end))

    async def drain_queue():
        while aggregator.queue:
            await aggregator.consume_batch()

    asyncio.run(drain_queue())

    assert len(queued) == 2
    assert len(FakeSession.requests) == len(queued)
    assert FakeSession.requests[0][1]["start_date"] == "2026-05-01T00:00:00"
    assert FakeSession.requests[-1][1]["end_date"] == "2026-06-01T00:00:00"
    assert log_path.exists()
    log_contents = log_path.read_text()
    assert log_contents.count("request method=GET") == len(queued)
    assert "apikey" not in log_contents
    assert "test-key" not in log_contents