from __future__ import annotations

from eval.connector import TickerplantConnector


def main() -> None:
    connector = TickerplantConnector(base_url="http://localhost:8000")
    symbol = "AAPL"
    start = "2024-01-01T00:00:00"
    end = "2024-02-29T23:59:59"

    print("Fetching pending work...")
    pending = connector.meta(symbol, start, end)
    print(pending)

    print("Posting sample minute data...")
    connector.data(
        {
            symbol: [
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

    print("Marking the first month as done...")
    done = connector.setdone(symbol, 2024, 1)
    print(done)


if __name__ == "__main__":
    main()
