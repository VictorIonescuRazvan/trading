from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


LOG_DIR = Path("/var/log/dataprovider")
CONFIG_LOG_PATH = LOG_DIR / "config.log"
REQUEST_LOG_PATH = LOG_DIR / "requests.log"
WORKER_QUEUE_LOG_PATH = LOG_DIR / "worker_queue.log"

_SYSLOG_NUMBERS = {
    logging.INFO: 6,
    logging.ERROR: 3,
    logging.CRITICAL: 2,
}


class DataproviderFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        severity = _SYSLOG_NUMBERS.get(record.levelno, 6)
        timestamp = self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        message = record.getMessage()
        return f"{timestamp}: dataprovider-{record.levelname.lower()}({severity})-{record.funcName}: {message}"


def _file_handler(path: Path) -> logging.FileHandler:
    handler = logging.FileHandler(path)
    handler.setFormatter(DataproviderFormatter())
    return handler


def _configure_logger(name: str, path: Path, level: int) -> None:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.addHandler(_file_handler(path))


def configure_logging() -> None:
    paths = (CONFIG_LOG_PATH, REQUEST_LOG_PATH, WORKER_QUEUE_LOG_PATH)
    try:
        if not LOG_DIR.is_dir() or not os.access(LOG_DIR, os.W_OK | os.X_OK):
            raise OSError(f"log directory is not usable: {LOG_DIR}")
        for path in paths:
            with path.open("a", encoding="utf-8"):
                pass
        _configure_logger("dataprovider.config", CONFIG_LOG_PATH, logging.INFO)
        _configure_logger("dataprovider.requests", REQUEST_LOG_PATH, logging.INFO)
        _configure_logger("dataprovider.worker_queue", WORKER_QUEUE_LOG_PATH, logging.INFO)
    except Exception as error:
        print(f"dataprovider logging initialization failed: {error}", file=sys.stdout, flush=True)
        raise RuntimeError("dataprovider log directory is not usable") from error


__all__ = [
    "CONFIG_LOG_PATH",
    "LOG_DIR",
    "REQUEST_LOG_PATH",
    "WORKER_QUEUE_LOG_PATH",
    "configure_logging",
]