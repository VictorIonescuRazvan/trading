# Eval Service

## Purpose

`eval` is a small Python FastAPI service that checks whether the tickerplant
reports data for a symbol and an inclusive ISO8601 date range.

## Runtime Architecture

```text
HTTP client
    |
    | GET /check?symbol=...&start=...&end=...
    v
eval.app FastAPI route
    |
    | TickerplantConnector.meta(...)
    v
tickerplant GET /meta
    |
    v
pending metadata rows
```

The service reads `/etc/eval/config.yaml` during FastAPI startup. The required
keys are:

```yaml
tickerplant_host: 127.0.0.1
tickerplant_port: 8017
```

The host and port are combined into an HTTP base URL. The connector uses a
synchronous `httpx.Client`, so `/check` is intentionally a synchronous FastAPI
route.

## API Contract

### `GET /check`

Required query parameters:

- `symbol`: ticker symbol passed unchanged to tickerplant.
- `start`: ISO8601 datetime string, for example `2026-07-24T18:00:00`.
- `end`: ISO8601 datetime string, for example `2026-07-24T19:00:00`.

The route forwards all three values to tickerplant `GET /meta`. Tickerplant
returns pending rows from `symbolMetadata`; therefore an empty response means
all requested metadata is complete, while one or more rows means data is still
missing for those months.

Successful response when the requested range is populated:

```json
{"data_exists": true}
```

When tickerplant reports any pending metadata for the requested range:

```json
{"data_exists": false}
```

The pending rows are used only to calculate the boolean and are not exposed by
the eval API.

Tickerplant failures are translated to HTTP 502. Missing or invalid local
configuration prevents startup with a clear runtime error.

## Implementation Layout

- `src/eval/app.py`: configuration loading, FastAPI app, and `/check` route.
- `packages/connector/src/connector/connector.py`: HTTP client for tickerplant.
- `tests/test_app.py`: route, forwarding, and configuration tests.
- `tests/test_connector.py`: connector integration tests against tickerplant's
  FastAPI app.

## Development

Install dependencies and run tests from `eval`:

```bash
uv sync
uv run pytest
```

Run the service with:

```bash
uv run fastapi run
```