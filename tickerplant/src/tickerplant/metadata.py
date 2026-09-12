from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Mapping

from .init_db import init_db
from .querylog import log_query

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
                select_query = """
                    SELECT status
                    FROM symbolMetadata
                    WHERE symbol = ? AND year = ? AND month = ?
                    """
                select_params = (symbol, year, month)
                log_query("metadata", "_push", select_query, select_params)
                existing = self.db.execute(select_query, select_params).fetchone()

                delete_query = """
                    DELETE FROM symbolMetadata
                    WHERE symbol = ? AND year = ? AND month = ?
                    """
                log_query("metadata", "_push", delete_query, select_params)
                self.db.execute(delete_query, select_params)

                final_status = max(existing[0], incoming_status) if existing else incoming_status
                insert_query = """
                    INSERT INTO symbolMetadata (symbol, year, month, status)
                    VALUES (?, ?, ?, ?)
                    """
                insert_params = (symbol, year, month, final_status)
                log_query("metadata", "_push", insert_query, insert_params)
                self.db.execute(insert_query, insert_params)
            self.db.commit()

    def _get(
        self,
        symbol: str | None,
        status: int,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[tuple[int, int]] | list[tuple[str, int, int]]:
        clauses: list[str] = []
        params: list[object] = []

        if symbol is not None:
            clauses.append("symbol = ?")
            params.append(symbol)

        clauses.append("status = ?")
        params.append(status)

        if start_date is not None and end_date is not None:
            month_keys = _month_keys(start_date, end_date)
            clauses.append(
                "(" + " OR ".join("(year = ? AND month = ?)" for _ in month_keys) + ")"
            )
            for year, month in month_keys:
                params.extend((year, month))
        elif start_date is not None:
            clauses.append("(year > ? OR (year = ? AND month >= ?))")
            params.extend((start_date.year, start_date.year, start_date.month))
        elif end_date is not None:
            clauses.append("(year < ? OR (year = ? AND month <= ?))")
            params.extend((end_date.year, end_date.year, end_date.month))

        with self._lock:
            query = f"""
                SELECT symbol, year, month
                FROM symbolMetadata
                WHERE {' AND '.join(clauses)}
                ORDER BY year, month
                """
            log_query("metadata", "_get", query, params)
            rows = self.db.execute(query, params).fetchall()

        if symbol is not None:
            return [(year, month) for _, year, month in rows]
        return [(row_symbol, year, month) for row_symbol, year, month in rows]

    def getPending(
        self,
        symbol: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[tuple[str, int, int]]:
        return self._get(symbol, status=0, start_date=start_date, end_date=end_date)

    def getDone(
        self,
        symbol: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[tuple[int, int]] | list[tuple[str, int, int]]:
        return self._get(symbol, status=1, start_date=start_date, end_date=end_date)

    def pushPending(self, values: MetadataMonths) -> None:
        self._push(values, status=0)

    def pushDone(self, values: MetadataMonths) -> None:
        self._push(values, status=1)
