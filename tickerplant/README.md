# Tickerplant

Tickerplant is a FastAPI service backed by SQLite. It stores minute-level market
data for ticker symbols and tracks which symbol/month metadata jobs are pending
or complete.

## Project layout

- `src/tickerplant/api.py` contains the FastAPI application.
- `src/tickerplant/dbquery.py` handles minute data in the `symbols` table.
- `src/tickerplant/metadata.py` handles work status in the `symbolMetadata` table.
- `src/tickerplant/init_db.py` applies the SQL schema files.
- `schemas/symbols.sql` and `schemas/symbolMetadata.sql` are the single source of
	truth for the database schema.
- `tests/` contains the pytest suite.

## Requirements

- Python 3.10 or newer
- `uv`

Install or synchronize dependencies from the project directory:

```bash
cd /home/victor/trading/tickerplant
uv sync
```

## Configuration

The service reads its runtime configuration from:

```text
/etc/tickerplant/config.yaml
```

The expected configuration is:

```yaml
metadata_port: 5001
data_port: 5000
db_file: /var/tickerplant/db.sql
```

The current FastAPI application listens on the port selected by the FastAPI/Uvicorn
command, normally `8000`; `metadata_port` and `data_port` are retained as service
configuration values but are not used by `api.py` to select separate listeners.

The configured database directory must exist and be writable. The application
creates the SQLite file and applies both schema files during startup.

## Run the API

Development mode with reload:

```bash
cd /home/victor/trading/tickerplant
uv run fastapi dev
```

Production-style serving:

```bash
cd /home/victor/trading/tickerplant
uv run fastapi run
```

The application is available at `http://127.0.0.1:8000`. Interactive API
documentation is available at `http://127.0.0.1:8000/docs`.

## API

### `POST /data`

Insert one or more minute records grouped by ticker symbol. The date can be an
ISO datetime with or without a timezone; timezone-naive dates are treated as UTC.

```bash
curl -i -X POST http://127.0.0.1:8000/data \
	-H 'Content-Type: application/json' \
	-d '{
		"data": {
			"AAPL": [
				{
					"date": "2024-01-15T14:30:00Z",
					"low": 184.10,
					"high": 185.20,
					"open": 184.50,
					"close": 184.90,
					"volume": 1200
				}
			]
		}
	}'
```

This returns `204 No Content` and inserts the row into the `symbols` table.

### `POST /getdata`

Return all stored data rows for the requested symbols and inclusive ISO date
range. This endpoint queries the `symbols` table directly and does not require
or check corresponding metadata entries. Symbols with no matching rows simply
produce no results.

```bash
curl -X POST http://127.0.0.1:8000/getdata \
	-H 'Content-Type: application/json' \
	-d '{
		"start": "2024-01-15T00:00:00Z",
		"end": "2024-01-15T23:59:59Z",
		"symbols": ["AAPL", "MSFT"]
	}'
```

The response is a JSON list of matching rows, including the stored `symbol`:

```json
[{"symbol":"AAPL","date":"2024-01-15T14:30:00Z","low":184.1,"high":185.2,"open":184.5,"close":184.9,"volume":1200}]
```

### `GET /meta`

Return pending metadata months for a ticker and inclusive ISO date range:

```bash
curl 'http://127.0.0.1:8000/meta?symbol=AAPL&start=2024-01-01T00:00:00Z&end=2024-03-31T23:59:59Z'
```

The response is a list such as:

```json
[{"year": 2024, "month": 1}]
```

`/meta` reads `symbolMetadata`; inserting data with `/data` does not automatically
create metadata rows.

### `POST /setdone`

Mark a symbol/month as complete. This is also the way to create a metadata row:

```bash
curl -i -X POST http://127.0.0.1:8000/setdone \
	-H 'Content-Type: application/json' \
	-d '{"symbol":"AAPL","year":2024,"month":1}'
```

The response echoes the validated metadata entry. A completed row is no longer
returned by `/meta` as pending.

Ticker symbols must be 1 to 6 characters and contain only letters, digits, or a
period. Values such as `NONE`, `NULL`, `NAN`, and `INF` are rejected.

## Tests

Run the test suite with:

```bash
cd /home/victor/trading/tickerplant
uv run pytest
```

Database tests use temporary SQLite files. Live startup uses the database path in
`/etc/tickerplant/config.yaml`.
