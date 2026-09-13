from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tickerplant import api


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    config_path = tmp_path / "config.yaml"
    database_path = tmp_path / "tickerplant.sqlite"
    config_path.write_text(f"db_file: {database_path}\n", encoding="utf-8")
    monkeypatch.setattr(api, "_config_path", config_path)

    with TestClient(api.app) as test_client:
        yield test_client

    if api.dbquery is not None:
        api.dbquery.db.close()
    if api.metadata is not None:
        api.metadata.db.close()
    api.dbquery = None
    api.metadata = None