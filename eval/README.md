# Eval

Eval is a FastAPI service that checks whether tickerplant has complete metadata
for a symbol and an ISO8601 date range.

## Configuration

The service reads `/etc/eval/config.yaml` at startup:

```yaml
tickerplant_host: 127.0.0.1
tickerplant_port: 8017
```

`tickerplant_host` and `tickerplant_port` identify the tickerplant API.

## Run

```bash
cd /home/victor/trading/eval
uv sync
uv run fastapi run
```

## API

`GET /check` forwards `symbol`, `start`, and `end` to tickerplant's `GET /meta`.
Because `/meta` returns pending metadata rows, `data_exists` is `true` only
when the pending list is empty.

```bash
curl 'http://127.0.0.1:8000/check?symbol=AAPL&start=2026-07-24T18:00:00&end=2026-07-24T19:00:00'
```

Successful responses contain only `data_exists`. Tickerplant request failures
return HTTP 502.

## Connector

The connector lives in `eval.connector.TickerplantConnector` and exposes three methods that map directly to the server endpoints in `tickerplant.api`:

### `meta(symbol: str, start: str, end: str) -> list[dict]`

Calls `GET /meta`.

Parameters:
- `symbol`: ticker symbol such as `AAPL`
- `start`: ISO datetime string, e.g. `2024-01-01T00:00:00`
- `end`: ISO datetime string, e.g. `2024-02-29T23:59:59`

Returns:
- a list of pending metadata rows like:

```python
[
  {"symbol": "AAPL", "year": 2024, "month": 1, "status": 0},
  {"symbol": "AAPL", "year": 2024, "month": 2, "status": 0},
]
```

The server creates missing month entries for the requested range and returns all pending rows.

### `data(data: dict[str, list[dict]]) -> None`

Calls `POST /data`.

Input shape:

```python
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
```

This is the same payload the FastAPI route expects as `{"data": {...}}`.

### `setdone(symbol: str, year: int, month: int) -> dict`

Calls `POST /setdone`.

Input:

```python
("AAPL", 2024, 1)
```

Returns:

```python
{"symbol": "AAPL", "year": 2024, "month": 1}
```

## Example

Start the Tickerplant API in another terminal, then run:

```bash
cd /home/victor/trading/workfolder/eval
PYTHONPATH=../tickerplant/src:src ./.venv/bin/python sample_connector.py
```

The sample script in `sample_connector.py` demonstrates:
1. fetching pending metadata,
2. pushing minute data,
3. marking a month done.

## Initialization

```python
from eval.connector import TickerplantConnector

connector = TickerplantConnector(base_url="http://localhost:8000")
```

You may also pass an existing `httpx.Client` instance if you need custom headers, timeouts, or transport configuration.
