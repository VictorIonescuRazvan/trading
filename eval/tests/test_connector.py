from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from eval.connector import TickerplantConnector
from tickerplant.api import app as tickerplant_app
from tickerplant.database import db


class TickerplantConnectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(tickerplant_app)
        self.connector = TickerplantConnector(base_url="http://testserver", client=self.client)
        self.symbol = "CONNECTOR_TEST"

    def tearDown(self) -> None:
        db.execute("DELETE FROM symbolMetadata WHERE symbol = ?", (self.symbol,))
        db.execute("DELETE FROM symbols WHERE symbol = ?", (self.symbol,))
        db.commit()

    def test_meta_data_and_setdone_round_trip(self) -> None:
        records = self.connector.meta(
            self.symbol,
            "2024-01-01T00:00:00",
            "2024-02-29T23:59:59",
        )
        months = {(row["year"], row["month"]) for row in records if row["symbol"] == self.symbol}
        self.assertEqual(months, {(2024, 1), (2024, 2)})

        self.connector.data(
            {
                self.symbol: [
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

        done = self.connector.setdone(self.symbol, 2024, 1)
        self.assertEqual(done, {"symbol": self.symbol, "year": 2024, "month": 1})


if __name__ == "__main__":
    unittest.main()
