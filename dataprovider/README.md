# Dataprovider

`dataprovider` is a background service that fills missing minute-level OHLCV
market data. It checks the tickerplant for pending symbol/month intervals,
fetches the data from a configured public market-data provider, and sends the
normalized records back to the tickerplant.

## How It Works

When the FastAPI application starts, it launches a polling loop that runs every
60 seconds:

1. Ask the tickerplant for pending work within the configured date range.
2. Split each pending month into provider-compatible intervals using the
   configured exchange calendar.
3. Fetch the intervals asynchronously in batches.
4. Push the normalized `date`, `open`, `high`, `low`, `close`, and `volume`
   records to the tickerplant.
5. Mark a month complete only after its data has been pushed successfully.

Failed provider requests are requeued. HTTP 429 responses wait before retrying.

## Requirements

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A reachable tickerplant service
- Access to a compatible public market-data API, currently the Twelve Data
  `time_series` endpoint
- A base64-encoded API key
- Write access to `/etc/dataprovider/config.yaml` and
  `/var/log/dataprovider/`

## Configuration

The service loads its configuration from `/etc/dataprovider/config.yaml`.
Create that file from `config.yaml.sample` and configure the tickerplant and
provider settings:

```yaml
tickerplant_host: localhost
tickerplant_port: 8000
symbols:
  - AAPL
start: 2024-01-01T00:00:00Z
end: 2024-12-31T23:59:59Z
dataprovider:
  batch_size: 8
  time_interval: 1
  max_query_size: 5000
  exchange_calendar: XNYS
  endpoint: https://api.twelvedata.com/time_series
  api_key_b64: <base64-encoded-api-key>
```

`symbols` may be empty to allow all pending symbols. `start` and `end` define
the range requested from the tickerplant. The provider endpoint and
`api_key_b64` are required; `batch_size`, `time_interval`, `max_query_size`,
and `exchange_calendar` have defaults.

## Paths and Logs

Runtime logs are written to:

- `/var/log/dataprovider/config.log`: loaded configuration
- `/var/log/dataprovider/requests.log`: tickerplant request activity
- `/var/log/dataprovider/worker_queue.log`: queue, provider, and data-push
  activity

## Start

From the project directory:

```bash
./start.bash
```

The script synchronizes dependencies and starts Uvicorn with the application
reload option on the default port, `8000`.

For a direct start without reload:

```bash
uv sync --link-mode=copy
uv run dataprovider
```

The installed `dataprovider` command serves the application on `0.0.0.0:8001`.
