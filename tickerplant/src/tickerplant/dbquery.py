from __future__ import annotations

import numbers
import sqlite3
import threading
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .querylog import log_query

SymbolRecord = Mapping[str, Any]
SymbolRecords = Mapping[str, Iterable[SymbolRecord]]


class DBQuery:
    """SQLite-backed store for minute symbol data."""

    def __init__(self, db_file: str | Path) -> None:
        db_path = Path(db_file)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()

    @staticmethod
    def _date_value(value: datetime | int) -> int:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return int(value.timestamp())
        if isinstance(value, bool) or not isinstance(value, numbers.Integral):
            raise TypeError("date must be a datetime or integer Unix timestamp")
        return int(value)

    @staticmethod
    def _number(value: Any, field: str) -> float | int:
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise TypeError(f"{field} must be a number")
        return value

    def _row(self, symbol: str, record: SymbolRecord) -> tuple[Any, ...]:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        if not isinstance(record, Mapping):
            raise TypeError("each symbol value must be a mapping")

        required = {"date", "low", "high", "open", "close", "volume"}
        missing = required - record.keys()
        if missing:
            raise ValueError(f"record is missing fields: {sorted(missing)}")

        volume = record["volume"]
        if isinstance(volume, bool) or not isinstance(volume, numbers.Integral):
            raise TypeError("volume must be an integer")

        return (
            symbol,
            self._date_value(record["date"]),
            self._number(record["low"], "low"),
            self._number(record["high"], "high"),
            self._number(record["open"], "open"),
            self._number(record["close"], "close"),
            int(volume),
        )

    def insert(self, values: SymbolRecords) -> None:
        if not isinstance(values, Mapping):
            raise TypeError("values must be a mapping keyed by symbol")

        rows = []
        for symbol, records in values.items():
            if isinstance(records, (str, bytes, Mapping)):
                raise TypeError("each symbol value must be an iterable of records")
            try:
                rows.extend(self._row(symbol, record) for record in records)
            except TypeError as exc:
                raise TypeError("each symbol value must be an iterable of records") from exc

        with self._lock:
            query = """
                INSERT INTO symbols (symbol, date, low, high, open, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
            for row in rows:
                log_query("dbquery", "insert", query, row)
            self.db.executemany(query, rows)
            self.db.commit()

    def select(
        self, symbol: str, start: datetime | int, end: datetime | int
    ) -> list[dict[str, Any]]:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        start_value = self._date_value(start)
        end_value = self._date_value(end)
        if start_value > end_value:
            raise ValueError("start must not be after end")

        with self._lock:
            query = """
                SELECT symbol, date, low, high, open, close, volume
                FROM symbols
                WHERE symbol = ? AND date BETWEEN ? AND ?
                ORDER BY date
                """
            params = (symbol, start_value, end_value)
            log_query("dbquery", "select", query, params)
            rows = self.db.execute(query, params).fetchall()

        return [
            {
                "symbol": row[0],
                "date": datetime.fromtimestamp(row[1], tz=timezone.utc),
                "low": row[2],
                "high": row[3],
                "open": row[4],
                "close": row[5],
                "volume": row[6],
            }
            for row in rows
        ]
