# Connector

The connector provides the client API used by applications to communicate
with the Tickerplant service. It is an abstraction layer between consumers and
the service's database-backed implementation.

## Architecture

The connector implementation may change over time while preserving the API
documented below. Code that uses the connector should depend only on this
exposed API and must not access or rely on its underlying implementation.

This boundary keeps consumers independent from the database implementation.
Tickerplant can therefore change how it stores, queries, or manages data
without requiring changes to every application that uses the connector.

## Installation

This package is part of the Eval workspace and uses `uv` for dependency
management. From the package directory:

```bash
uv sync
```

## API

### `TickerplantConnector`

Create a connector with the Tickerplant base URL. An existing `httpx.Client`
can be supplied when custom headers, timeouts, or transport configuration are
needed.

```python
from connector.connector import TickerplantConnector

connector = TickerplantConnector(base_url="http://localhost:8000")
```

#### `meta(symbol: str, start: str, end: str) -> list[dict[str, Any]]`

Fetches pending metadata for a symbol and ISO 8601 date range.

```python
pending = connector.meta(
	symbol="AAPL",
	start="2024-01-01T00:00:00",
	end="2024-02-29T23:59:59",
)
```

The result is a list of metadata rows, for example:

```python
[
	{"year": 2024, "month": 1},
	{"year": 2024, "month": 2},
]
```

#### `getpending(start: str, end: str) -> list[dict[str, Any]]`

Fetches pending metadata for all symbols in an ISO 8601 date range.

```python
pending = connector.getpending(
	start="2024-01-01T00:00:00",
	end="2024-02-29T23:59:59",
)
```

#### `getdata(start: str, end: str, symbols: list[str]) -> list[dict[str, Any]]`

Fetches market data for the requested symbols and ISO 8601 date range.

```python
records = connector.getdata(
	start="2024-01-02T14:30:00Z",
	end="2024-01-02T14:31:00Z",
	symbols=["AAPL"],
)
```

#### `data(data: dict[str, list[dict[str, Any]]]) -> None`

Submits market data grouped by symbol.

```python
connector.data(
	{
		"AAPL": [
			{
				"date": "2024-01-02T14:30:00Z",
				"low": 184.2,
				"high": 184.65,
				"open": 184.3,
				"close": 184.55,
				"volume": 12500,
			}
		]
	}
)
```

#### `setdone(symbol: str, year: int, month: int) -> dict[str, Any]`

Marks a symbol's month as complete and returns the resulting metadata.

```python
result = connector.setdone("AAPL", 2024, 1)
# {"symbol": "AAPL", "year": 2024, "month": 1}
```

The connector raises an HTTP error when the Tickerplant service returns an
unsuccessful response.
