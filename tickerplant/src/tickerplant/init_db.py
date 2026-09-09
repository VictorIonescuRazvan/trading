from __future__ import annotations

from pathlib import Path
import sqlite3
from collections.abc import Iterable


def init_db(db_path: str | Path, schema_paths: Iterable[Path]) -> None:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_file)
    try:
        for schema_path in schema_paths:
            if not schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_path}")

            sql = schema_path.read_text(encoding="utf-8")
            connection.executescript(sql)

        connection.commit()
        print(f"Initialized SQLite database at: {db_file}")
        print("Used schema files:")
        for schema_path in schema_paths:
            print(f" - {schema_path.name}")
    finally:
        connection.close()