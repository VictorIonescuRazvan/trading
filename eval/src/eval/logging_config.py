from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


LOG_DIR = Path("/var/log/eval")
REQUEST_LOG_PATH = LOG_DIR / "requests.log"
CONNECTOR_LOG_PATH = LOG_DIR / "connector.log"

_SYSLOG_NUMBERS = {
    logging.INFO: 6,
    logging.ERROR: 3,
    logging.CRITICAL: 2,
}


class EvalFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        severity = _SYSLOG_NUMBERS.get(record.levelno, 6)
        timestamp = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%dT%H:%M:%S.%f"
        )[:-3]
        return f"{timestamp}:eval-{severity}-{record.funcName}:{record.getMessage()}"


def _configure_logger(name: str, path: Path) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.FileHandler(path)
    handler.setFormatter(EvalFormatter())
    logger.addHandler(handler)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _configure_logger("eval.requests", REQUEST_LOG_PATH)
    _configure_logger("eval.connector", CONNECTOR_LOG_PATH)


__all__ = [
    "CONNECTOR_LOG_PATH",
    "EvalFormatter",
    "LOG_DIR",
    "REQUEST_LOG_PATH",
    "configure_logging",
]