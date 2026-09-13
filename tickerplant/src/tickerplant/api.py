from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dbquery import DBQuery
from .init_db import init_db
from .metadata import Metadata
from .querylog import log_request


class MetadataEntry(BaseModel):
    symbol: str = Field(min_length=1)
    year: int = Field(ge=1)
    month: int = Field(ge=1, le=12)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not _is_ticker(value):
            raise ValueError("symbol must be a valid stock ticker")
        return value


class MinuteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime
    low: float
    high: float
    open: float
    close: float
    volume: int

    @field_validator("date")
    @classmethod
    def require_aware_date(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class DataRequest(BaseModel):
    data: dict[str, list[MinuteRecord]] = Field(min_length=1)


class GetDataRequest(BaseModel):
    start: datetime
    end: datetime
    symbols: list[str] = Field(min_length=1)

    @field_validator("start", "end")
    @classmethod
    def require_aware_date(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _parse_iso(value: str, name: str) -> datetime:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must be an ISO datetime, for example 2006-01-02T15:04:05",
        ) from exc


def _month_keys(start: datetime, end: datetime) -> list[tuple[int, int]]:
    year, month = start.year, start.month
    keys: list[tuple[int, int]] = []
    while (year, month) <= (end.year, end.month):
        keys.append((year, month))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return keys


_TICKER_RE = re.compile(r"^[A-Za-z0-9.]{1,6}$")
_DISALLOWED_TICKERS = {"NONE", "NULL", "NAN", "INF", "N/A"}
def _is_ticker(value: str) -> bool:
    """Return True when a value looks like a stock ticker symbol."""
    if not isinstance(value, str):
        return False
    if not value or len(value) > 6:
        return False

    normalized = value.strip()
    if normalized != value:
        return False
    if value.upper() in _DISALLOWED_TICKERS:
        return False
    return bool(_TICKER_RE.fullmatch(value))


def _sanitize_meta(symbol: str, start: str, end: str) -> tuple[str, datetime, datetime]:
    if not _is_ticker(symbol):
        raise HTTPException(status_code=422, detail="symbol must be a valid stock ticker")

    start_date = _parse_iso(start, "start")
    end_date = _parse_iso(end, "end")
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start must not be after end")

    return symbol, start_date, end_date


_schemas_root = Path(__file__).resolve().parents[2] / "schemas"
_config_path = Path("/etc/tickerplant/config.yaml")

dbquery: DBQuery | None = None
metadata: Metadata | None = None

app = FastAPI(title="Tickerplant API")


@app.middleware("http")
async def log_received_request(request: Request, call_next: Any) -> Any:
    body = await request.body()
    request_line = f"{request.method} {request.url.path}"
    if request.url.query:
        request_line += f"?{request.url.query}"
    if body:
        request_body = " ".join(body.decode("utf-8", errors="replace").split())
        request_line += f" {request_body}"
    log_request("api", "request", request_line)
    return await call_next(request)


@app.on_event("startup")
def initialize_database() -> None:
    global dbquery, metadata

    if not _config_path.exists():
        raise RuntimeError(f"Config file not found: {_config_path}")

    with open(_config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    config_db_path = config.get("db_file")
    if not config_db_path:
        raise RuntimeError(f"db_file not found in config.yaml: {_config_path}")

    db_path = Path(config_db_path)
    if not db_path.is_absolute():
        db_path = (_config_path.parent / db_path).resolve()

    schema_paths = list(_schemas_root.glob("*.sql"))
    init_db(db_path, schema_paths)
    dbquery = DBQuery(db_path)
    metadata = Metadata(db_path)


@app.get("/meta")
def get_metadata(
    symbol: Annotated[str, Query(min_length=1)],
    start: Annotated[str, Query()],
    end: Annotated[str, Query()],
) -> list[dict[str, Any]]:
    if metadata is None:
        raise HTTPException(status_code=500, detail="database is not initialized")

    _, start_date, end_date = _sanitize_meta(symbol, start, end)
    try:
        pending = metadata.getPending(symbol, start_date, end_date)
        done = metadata.getDone(symbol, start_date, end_date)
        known = set(pending) | set(done)
        for month in _month_keys(start_date, end_date):
            if month not in known:
                metadata.pushPending({symbol: month})

        retvalue = [
            {"year": year, "month": month}
            for year, month in metadata.getPending(symbol, start_date, end_date)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving metadata")

    return retvalue

@app.get("/getpending")
def get_pending(
    start: Annotated[str, Query()],
    end: Annotated[str, Query()],
) -> list[dict[str, Any]]:
    if metadata is None:
        raise HTTPException(status_code=500, detail="database is not initialized")

    _, start_date, end_date = _sanitize_meta("A", start, end)
    try:
        return [
            {"symbol": symbol, "year": year, "month": month}
            for symbol, year, month in metadata.getPending(None, start_date, end_date)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving metadata") from e

@app.post("/data", status_code=204)
def push_data(request: DataRequest) -> None:
    if dbquery is None:
        raise HTTPException(status_code=500, detail="database is not initialized")

    try:
        dbquery.insert(
            {
                symbol: [record.model_dump() for record in records]
                for symbol, records in request.data.items()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error inserting data")


@app.post("/getdata")
def get_data(request: GetDataRequest) -> list[dict[str, Any]]:
    if dbquery is None:
        raise HTTPException(status_code=500, detail="database is not initialized")
    if request.start > request.end:
        raise HTTPException(status_code=422, detail="start must not be after end")

    try:
        return [
            record
            for symbol in request.symbols
            for record in dbquery.select(symbol, request.start, request.end)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error retrieving data") from e


@app.post("/setdone", response_model=MetadataEntry)
def set_done(entry: MetadataEntry) -> MetadataEntry:
    if metadata is None:
        raise HTTPException(status_code=500, detail="database is not initialized")

    try:
        metadata.pushDone({entry.symbol: (entry.year, entry.month)})
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error setting done")

    return entry
