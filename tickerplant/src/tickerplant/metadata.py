from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Mapping

from .init_db import init_db

MetadataMonths = Mapping[str, tuple[int, int]]


def _month_keys(start_date: datetime, end_date: datetime) -> list[tuple[int, int]]:
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")

    out: list[tuple[int, int]] = []
    year, month = start_date.year, start_date.month
    end_year, end_month = end_date.year, end_date.month

    while (year, month) <= (end_year, end_month):
        out.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1

    return out


class Metadata:
    """SQLite-backed interface for the symbolMetadata table."""

    def __init__(self, db_file: str | Path) -> None:
        db_path = Path(db_file)
        schemas_root = Path(__file__).resolve().parents[2] / "schemas"
        init_db(db_path, [schemas_root / "symbolMetadata.sql", schemas_root / "symbols.sql"])
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._connection = self.db
        self._lock = threading.Lock()

    @staticmethod
    def _validate(year: int, month: int) -> None:
        if not isinstance(year, int) or not isinstance(month, int):
            raise TypeError("metadata year and month must be integers")
        if not 1 <= month <= 12:
            raise ValueError("metadata month must be between 1 and 12")

    def _push(self, values: MetadataMonths, status: int) -> None:
        rows = []
        for symbol, (year, month) in values.items():
            self._validate(year, month)
            rows.append((symbol, year, month, status))

        with self._lock:
            for symbol, year, month, incoming_status in rows:
                existing = self.db.execute(
                    """
                    SELECT status
                    FROM symbolMetadata
                    WHERE symbol = ? AND year = ? AND month = ?
                    """,
                    (symbol, year, month),
                ).fetchone()
                self.db.execute(
                    """
                    DELETE FROM symbolMetadata
                    WHERE symbol = ? AND year = ? AND month = ?
                    """,
                    (symbol, year, month),
                )

                final_status = max(existing[0], incoming_status) if existing else incoming_status
                self.db.execute(
                    """
                    INSERT INTO symbolMetadata (symbol, year, month, status)
                    VALUES (?, ?, ?, ?)
                    """,
                    (symbol, year, month, final_status),
                )
            self.db.commit()

    def _get(
        self,
        symbol: str,
        status: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[tuple[int, int]]:
        month_keys = _month_keys(start_date, end_date)
        if not month_keys:
            return []

        clause = " OR ".join("(year = ? AND month = ?)" for _ in month_keys)
        params: list[object] = [symbol, status]
        for year, month in month_keys:
            params.extend((year, month))

        with self._lock:
            rows = self.db.execute(
                f"""
                SELECT year, month
                FROM symbolMetadata
                WHERE symbol = ? AND status = ? AND ({clause})
                ORDER BY year, month
                """,
                params,
            ).fetchall()

        return [(year, month) for year, month in rows]

    def getPending(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[tuple[int, int]]:
        return self._get(symbol, status=0, start_date=start_date, end_date=end_date)

    def getDone(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[tuple[int, int]]:
        return self._get(symbol, status=1, start_date=start_date, end_date=end_date)

    def pushPending(self, values: MetadataMonths) -> None:
        self._push(values, status=0)

    def pushDone(self, values: MetadataMonths) -> None:
        self._push(values, status=1)
