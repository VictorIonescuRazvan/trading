from pathlib import Path

from fastapi.testclient import TestClient

import tickerplant.api as api
import tickerplant.querylog as querylog


def test_data_setdone_and_meta_endpoints(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "tickerplant.db"
    config_path.write_text(f"db_file: {db_path}\n", encoding="utf-8")
    monkeypatch.setattr(api, "_config_path", Path(config_path))

    with TestClient(api.app) as client:
        response = client.get(
            "/meta",
            params={
                "symbol": "ZZZ9",
                "start": "2024-02-01T00:00:00Z",
                "end": "2024-02-29T23:59:59Z",
            },
        )
        assert response.status_code == 200
        assert response.json() == []

        response = client.post(
            "/data",
            json={
                "data": {
                    "ZZZ9": [
                        {
                            "date": "2024-02-15T14:30:00Z",
                            "low": 10.0,
                            "high": 11.0,
                            "open": 10.5,
                            "close": 10.8,
                            "volume": 100,
                        }
                    ]
                }
            },
        )
        assert response.status_code == 204

        response = client.post(
            "/setdone",
            json={"symbol": "ZZZ9", "year": 2024, "month": 2},
        )
        assert response.status_code == 200
        assert response.json() == {"symbol": "ZZZ9", "year": 2024, "month": 2}

        response = client.get(
            "/meta",
            params={
                "symbol": "ZZZ9",
                "start": "2024-02-01T00:00:00Z",
                "end": "2024-02-29T23:59:59Z",
            },
        )
        assert response.status_code == 200
        assert response.json() == []

    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("SELECT symbol, volume FROM symbols").fetchall() == [
            ("ZZZ9", 100)
        ]
        assert connection.execute(
            "SELECT symbol, year, month, status FROM symbolMetadata"
        ).fetchall() == [("ZZZ9", 2024, 2, 1)]
    finally:
        connection.close()


def test_getdata_queries_data_without_metadata_validation(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "tickerplant.db"
    config_path.write_text(f"db_file: {db_path}\n", encoding="utf-8")
    monkeypatch.setattr(api, "_config_path", Path(config_path))

    with TestClient(api.app) as client:
        response = client.post(
            "/data",
            json={
                "data": {
                    "UNVERIFIED_SYMBOL": [
                        {
                            "date": "2024-02-15T14:30:00Z",
                            "low": 10.0,
                            "high": 11.0,
                            "open": 10.5,
                            "close": 10.8,
                            "volume": 100,
                        }
                    ]
                }
            },
        )
        assert response.status_code == 204

        response = client.post(
            "/getdata",
            json={
                "start": "2024-02-15T00:00:00Z",
                "end": "2024-02-15T23:59:59Z",
                "symbols": ["UNVERIFIED_SYMBOL", "MISSING"],
            },
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "symbol": "UNVERIFIED_SYMBOL",
            "date": "2024-02-15T14:30:00Z",
            "low": 10.0,
            "high": 11.0,
            "open": 10.5,
            "close": 10.8,
            "volume": 100,
        }
    ]


def test_api_logs_received_requests(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "tickerplant.db"
    request_log_path = tmp_path / "requests.log"
    config_path.write_text(f"db_file: {db_path}\n", encoding="utf-8")
    monkeypatch.setattr(api, "_config_path", Path(config_path))
    monkeypatch.setattr(querylog, "REQUEST_LOG_PATH", request_log_path)

    with TestClient(api.app) as client:
        response = client.get("/meta", params={"symbol": "AAPL", "start": "2024-01-01", "end": "2024-01-31"})

    assert response.status_code == 200
    assert "api-7-request: GET /meta?symbol=AAPL&start=2024-01-01&end=2024-01-31" in request_log_path.read_text()