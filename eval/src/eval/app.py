from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Annotated, Any

import yaml
from fastapi import FastAPI, HTTPException, Query, Request

from eval.connector import TickerplantConnector
from eval.logging_config import configure_logging

CONFIG_PATH = Path("/etc/eval/config.yaml")


@dataclass(frozen=True)
class EvalConfig:
    tickerplant_host: str
    tickerplant_port: int

    @property
    def tickerplant_url(self) -> str:
        return f"http://{self.tickerplant_host}:{self.tickerplant_port}"


def load_config(path: Path = CONFIG_PATH) -> EvalConfig:
    if not path.exists():
        raise RuntimeError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        values = yaml.safe_load(handle) or {}

    host = values.get("tickerplant_host")
    port = values.get("tickerplant_port")
    if not host or not isinstance(port, int) or isinstance(port, bool):
        raise RuntimeError(
            f"tickerplant_host and integer tickerplant_port are required in {path}"
        )
    if not 1 <= port <= 65535:
        raise RuntimeError(f"tickerplant_port must be between 1 and 65535 in {path}")

    return EvalConfig(tickerplant_host=str(host), tickerplant_port=port)


app = FastAPI(title="Eval API")
request_logger = logging.getLogger("eval.requests")


@app.on_event("startup")
def initialize_connector() -> None:
    configure_logging()
    config = load_config()
    app.state.connector = TickerplantConnector(base_url=config.tickerplant_url)


@app.get("/check")
def check_data(
    request: Request,
    symbol: Annotated[str, Query(min_length=1)],
    start: Annotated[str, Query()],
    end: Annotated[str, Query()],
) -> dict[str, Any]:
    connector = getattr(request.app.state, "connector", None)
    if connector is None:
        raise HTTPException(status_code=500, detail="eval is not initialized")

    request_logger.info("request received symbol=%s start=%s end=%s", symbol, start, end)
    try:
        pending = connector.meta(symbol, start, end)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="tickerplant request failed") from exc

    return {"data_exists": not pending}