from fastapi.testclient import TestClient


def test_api_endpoints_as_a_code_sample(client: TestClient) -> None:
    """A small example showing the normal workflow through every endpoint."""
    data = {
        "data": {
            "AAPL": [
                {
                    "date": "2024-01-15T14:30:00Z",
                    "low": 184.10,
                    "high": 185.20,
                    "open": 184.50,
                    "close": 184.90,
                    "volume": 1200,
                }
            ]
        }
    }

    assert client.post("/data", json=data).status_code == 204

    assert client.get(
        "/meta",
        params={
            "symbol": "AAPL",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-31T23:59:59Z",
        },
    ).json() == [{"year": 2024, "month": 1}]

    assert client.get(
        "/getpending",
        params={
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-31T23:59:59Z",
        },
    ).json() == [{"symbol": "AAPL", "year": 2024, "month": 1}]

    assert client.post(
        "/setdone", json={"symbol": "AAPL", "year": 2024, "month": 1}
    ).json() == {"symbol": "AAPL", "year": 2024, "month": 1}

    assert client.get(
        "/meta",
        params={
            "symbol": "AAPL",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-31T23:59:59Z",
        },
    ).json() == []

    assert client.post(
        "/getdata",
        json={
            "start": "2024-01-15T00:00:00Z",
            "end": "2024-01-15T23:59:59Z",
            "symbols": ["AAPL"],
        },
    ).json() == [
        {
            "symbol": "AAPL",
            "date": "2024-01-15T14:30:00Z",
            "low": 184.1,
            "high": 185.2,
            "open": 184.5,
            "close": 184.9,
            "volume": 1200,
        }
    ]