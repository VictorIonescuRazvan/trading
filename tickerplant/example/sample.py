from __future__ import annotations

from fastapi.testclient import TestClient

from .api import app
from .database import db


SYMBOL = "SAMPLE_API"


def main() -> None:
    client = TestClient(app)
    try:
        metadata_response = client.get(
            "/meta",
            params={
                "symbol": SYMBOL,
                "start": "2024-01-01T00:00:00",
                "end": "2024-02-29T23:59:59",
            },
        )
        assert metadata_response.status_code == 200
        months = {(row["year"], row["month"]) for row in metadata_response.json() if row["symbol"] == SYMBOL}
        assert months == {(2024, 1), (2024, 2)}
        print("/meta: ok")

        data_response = client.post(
            "/data",
            json={
                "data": {
                    SYMBOL: [
                        {
                            "date": "2024-01-02T14:30:00Z",
                            "low": 184.20,
                            "high": 184.65,
                            "open": 184.30,
                            "close": 184.55,
                            "volume": 12500,
                        },
                        {
                            "date": "2024-01-02T14:31:00Z",
                            "low": 184.45,
                            "high": 184.90,
                            "open": 184.55,
                            "close": 184.80,
                            "volume": 13100,
                        },
                    ]
                }
            },
        )
        assert data_response.status_code == 204
        print("/data: ok")

        done_response = client.post(
            "/setdone",
            json={"symbol": SYMBOL, "year": 2024, "month": 1},
        )
        assert done_response.status_code == 200
        assert done_response.json() == {
            "symbol": SYMBOL,
            "year": 2024,
            "month": 1,
        }
        print("/setdone: ok")
    finally:
        db.execute("DELETE FROM symbolMetadata WHERE symbol = ?", (SYMBOL,))
        db.execute("DELETE FROM symbols WHERE symbol = ?", (SYMBOL,))
        db.commit()


if __name__ == "__main__":
    main()
