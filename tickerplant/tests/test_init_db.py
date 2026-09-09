from datetime import datetime, timezone
from pathlib import Path

from tickerplant.dbquery import DBQuery
from tickerplant.init_db import init_db


SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"


def test_schema_dir_points_to_project_root_schemas() -> None:
    assert SCHEMA_DIR == Path(__file__).resolve().parents[1] / "schemas"
    assert (SCHEMA_DIR / "symbolMetadata.sql").exists()
    assert (SCHEMA_DIR / "symbols.sql").exists()


def test_init_db_creates_schema_tables(tmp_path) -> None:
    db_path = tmp_path / "nested" / "db.sql"
    init_db(db_path, [SCHEMA_DIR / "symbols.sql", SCHEMA_DIR / "symbolMetadata.sql"])

    assert db_path.exists()
    connection = __import__("sqlite3").connect(db_path)
    try:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='symbolMetadata'"
        ).fetchone()
        assert table is not None
    finally:
        connection.close()


def test_dbquery_connects_to_a_supplied_db_file(tmp_path) -> None:
    db_path = tmp_path / "quotes.db"
    init_db(db_path, [SCHEMA_DIR / "symbols.sql", SCHEMA_DIR / "symbolMetadata.sql"])

    query = DBQuery(db_path)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    query.insert(
        {
            "AAPL": [
                {
                    "date": start,
                    "low": 10.0,
                    "high": 12.0,
                    "open": 11.0,
                    "close": 11.5,
                    "volume": 100,
                },
                {
                    "date": end,
                    "low": 11.0,
                    "high": 13.0,
                    "open": 12.0,
                    "close": 12.5,
                    "volume": 200,
                },
            ]
        }
    )

    rows = query.select("AAPL", start, end)
    assert [row["close"] for row in rows] == [11.5, 12.5]
