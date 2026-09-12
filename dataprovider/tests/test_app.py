import asyncio

from dataprovider.app import poll_once


class FakeConnector:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def getpending(self, start: str, end: str) -> list[dict[str, object]]:
        self.calls.append(("getpending", start, end))
        return [
            {"symbol": "AAPL", "year": 2024, "month": 1},
            {"symbol": "MSFT", "year": 2024, "month": 1},
        ]

    def data(self, payload: dict[str, list[dict[str, object]]]) -> None:
        self.calls.append(("data", payload))

    def setdone(self, symbol: str, year: int, month: int) -> dict[str, object]:
        self.calls.append(("setdone", symbol, year, month))
        return {"symbol": symbol, "year": year, "month": month}


class FakeAggregator:
    def __init__(self) -> None:
        self.queue: list[tuple] = []

    def split_query(self, query: tuple) -> list[tuple]:
        return [query]

    async def consume_batch(self) -> list[dict[str, str]]:
        self.queue.pop(0)
        return [{
            "2024-01-02T14:30:00Z": {
                "datetime": "2024-01-02T14:30:00Z",
                "open": "1",
                "high": "2",
                "low": "0",
                "close": "1.5",
                "volume": "10",
            }
        }]


def test_poll_once_uses_getpending_and_pushes_before_setdone() -> None:
    connector = FakeConnector()
    aggregator = FakeAggregator()

    asyncio.run(
        poll_once(
            {
                "tickerplant": {"url": "http://tickerplant.test"},
                "symbols": ["AAPL"],
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-02-01T00:00:00Z",
            },
            connector,
            aggregator,
        )
    )

    assert connector.calls[0] == (
        "getpending",
        "2024-01-01T00:00:00Z",
        "2024-02-01T00:00:00Z",
    )
    assert [call[0] for call in connector.calls] == ["getpending", "data", "setdone"]
    assert connector.calls[1][1] == {
        "AAPL": [
            {
                "date": "2024-01-02T14:30:00Z",
                "open": 1.0,
                "high": 2.0,
                "low": 0.0,
                "close": 1.5,
                "volume": 10,
            }
        ]
    }
    assert connector.calls[2][1:] == ("AAPL", 2024, 1)
