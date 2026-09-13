from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tickerplant import api


def test_entered_data_matches_query_and_database_tables(client: TestClient) -> None:
    records = [
        {
            "date": "2024-01-15T14:30:00Z",
            "low": 184.10,
            "high": 185.20,
            "open": 184.50,
            "close": 184.90,
            "volume": 1200,
        },
        {
            "date": "2024-02-20T15:31:00",
            "low": 186.10,
            "high": 187.20,
            "open": 186.50,
            "close": 186.90,
            "volume": 2300,
        },
    ]

    assert client.post("/data", json={"data": {"MSFT": records}}).status_code == 204
    assert client.post(
        "/setdone", json={"symbol": "MSFT", "year": 2024, "month": 1}
    ).status_code == 200

    queried = client.post(
        "/getdata",
        json={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-02-29T23:59:59Z",
            "symbols": ["MSFT"],
        },
    ).json()

    assert queried == [
        {
            "symbol": "MSFT",
                "date": "2024-01-15T14:30:00Z",
            **records[0],
        },
        {
            "symbol": "MSFT",
                "date": "2024-02-20T15:31:00Z",
                **{**records[1], "date": "2024-02-20T15:31:00Z"},
        },
    ]

    assert api.dbquery is not None
    symbol_rows = api.dbquery.db.execute(
        "SELECT symbol, date, low, high, open, close, volume "
        "FROM symbols ORDER BY date"
    ).fetchall()
    assert symbol_rows == [
        (
            "MSFT",
            int(datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc).timestamp()),
            184.1,
            185.2,
            184.5,
            184.9,
            1200,
        ),
        (
            "MSFT",
            int(datetime(2024, 2, 20, 15, 31, tzinfo=timezone.utc).timestamp()),
            186.1,
            187.2,
            186.5,
            186.9,
            2300,
        ),
    ]

    assert api.metadata is not None
    metadata_rows = api.metadata.db.execute(
        "SELECT symbol, year, month, status "
        "FROM symbolMetadata ORDER BY year, month"
    ).fetchall()
    assert metadata_rows == [("MSFT", 2024, 1, 1)]