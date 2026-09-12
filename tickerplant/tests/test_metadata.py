import os
from datetime import datetime, timezone
from pathlib import Path

from tickerplant.metadata import Metadata


def test_metadata_accepts_db_path_and_queries_interval(tmp_path):
    db_path = tmp_path / "tickers.db"
    metadata = Metadata(db_path)

    metadata._connection.execute(
        "INSERT INTO symbolMetadata (symbol, year, month, status) VALUES (?, ?, ?, ?)",
        ("AAPL", 2024, 1, 0),
    )
    metadata._connection.execute(
        "INSERT INTO symbolMetadata (symbol, year, month, status) VALUES (?, ?, ?, ?)",
        ("AAPL", 2024, 2, 1),
    )
    metadata._connection.execute(
        "INSERT INTO symbolMetadata (symbol, year, month, status) VALUES (?, ?, ?, ?)",
        ("AAPL", 2024, 3, 0),
    )
    metadata._connection.execute(
        "INSERT INTO symbolMetadata (symbol, year, month, status) VALUES (?, ?, ?, ?)",
        ("MSFT", 2024, 2, 0),
    )
    metadata._connection.commit()

    start = datetime(2024, 1, 15, tzinfo=timezone.utc)
    end = datetime(2024, 3, 31, tzinfo=timezone.utc)

    assert metadata.getPending("AAPL", start, end) == [(2024, 1), (2024, 3)]
    assert metadata.getDone("AAPL", start, end) == [(2024, 2)]


def test_metadata_supports_symbol_wide_and_optional_date_queries(tmp_path):
    metadata = Metadata(tmp_path / "tickers.db")
    metadata.pushPending({"AAPL": (2024, 1), "MSFT": (2024, 2)})
    metadata.pushDone({"AAPL": (2024, 2)})

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 2, 28, tzinfo=timezone.utc)

    assert metadata.getPending(None, start, end) == [
        ("AAPL", 2024, 1),
        ("MSFT", 2024, 2),
    ]
    assert metadata.getDone(None, None, None) == [("AAPL", 2024, 2)]
    assert metadata.getPending("AAPL", None, None) == [(2024, 1)]
