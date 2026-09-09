from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from eval.app import EvalConfig, app, load_config


class StubConnector:
    def __init__(self, records: list[dict]) -> None:
        self.records = records
        self.calls: list[tuple[str, str, str]] = []

    def meta(self, symbol: str, start: str, end: str) -> list[dict]:
        self.calls.append((symbol, start, end))
        return self.records


def test_check_reports_data_exists_when_no_months_are_pending() -> None:
    connector = StubConnector([])
    with patch("eval.app.load_config", return_value=EvalConfig("localhost", 8017)), patch(
        "eval.app.TickerplantConnector", return_value=connector
    ):
        with TestClient(app) as client:
            response = client.get(
                "/check",
                params={
                    "symbol": "AAPL",
                    "start": "2026-07-24T18:00:00",
                    "end": "2026-07-24T19:00:00",
                },
            )

    assert response.status_code == 200
    assert response.json() == {"data_exists": True}
    assert connector.calls == [("AAPL", "2026-07-24T18:00:00", "2026-07-24T19:00:00")]


def test_check_reports_missing_data_when_month_is_pending() -> None:
    connector = StubConnector([{"year": 2026, "month": 7}])
    with patch("eval.app.load_config", return_value=EvalConfig("localhost", 8017)), patch(
        "eval.app.TickerplantConnector", return_value=connector
    ):
        with TestClient(app) as client:
            response = client.get(
                "/check?symbol=AAPL&start=2026-07-01T00:00:00&end=2026-07-31T23:59:59"
            )

    assert response.status_code == 200
    assert response.json() == {"data_exists": False}


def test_load_config_reads_host_and_port(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "tickerplant_host: tickerplant.internal\ntickerplant_port: 8017\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.tickerplant_url == "http://tickerplant.internal:8017"