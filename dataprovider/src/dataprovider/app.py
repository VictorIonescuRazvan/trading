from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from .aggregator import Aggregator


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


def _load_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    if not isinstance(config, dict):
        raise RuntimeError("config.yaml must contain a mapping")
    return config


CONFIG = _load_config()
APP_CONFIG = CONFIG.get("app", {})
DATAPROVIDER_CONFIG = CONFIG.get("dataprovider", {})
if not isinstance(APP_CONFIG, dict) or not isinstance(DATAPROVIDER_CONFIG, dict):
    raise RuntimeError("config.yaml must contain app and dataprovider mappings")
app = FastAPI(title="Trading Data API")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"errors": exc.errors()})


def _bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"errors": [message]})


def _parse_date(value: str, name: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise _bad_request(f"{name} must be an ISO datetime") from exc


@app.get("/populate", status_code=200, response_class=Response)
async def populate(
    symbols: Annotated[str, Query(min_length=1)],
    start_date: Annotated[str, Query(min_length=1)],
    end_date: Annotated[str, Query(min_length=1)],
) -> Response:
    symbol_list = [symbol.strip() for symbol in symbols.split(",") if symbol.strip()]
    if not symbol_list:
        raise _bad_request("symbols must contain at least one ticker")

    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")
    if start > end:
        raise _bad_request("start_date must not be after end_date")

    query = {
        symbol: {
            "start_date": start,
            "end_date": end,
        }
        for symbol in symbol_list
    }

    try:
        aggregator = Aggregator(CONFIG, query)
        combined, errors = await aggregator.aggregate()
    except ValueError as exc:
        raise _bad_request(str(exc)) from exc

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    limit = int(APP_CONFIG.get("max_elements", 100000))
    if len(combined) > limit:
        raise HTTPException(
            status_code=500,
            detail={"error": f"element limit exceeded: {len(combined)} > {limit}"},
        )
    return Response(status_code=200)