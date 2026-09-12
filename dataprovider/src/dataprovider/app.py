from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from connector.connector import TickerplantConnector
from fastapi import FastAPI

from .aggregator import Aggregator
from .logging_config import configure_logging


CONFIG_PATH = Path("/etc/dataprovider/config.yaml")
POLL_INTERVAL_SECONDS = 60
config_logger = logging.getLogger("dataprovider.config")
worker_queue_logger = logging.getLogger("dataprovider.worker_queue")


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
	with path.open("r", encoding="utf-8") as handle:
		config = yaml.safe_load(handle) or {}
	if not isinstance(config, dict):
		raise ValueError("configuration must be a mapping")
	return config


def _loggable_config(config: dict[str, Any]) -> dict[str, Any]:
	loggable = dict(config)
	dataprovider_config = loggable.get("dataprovider")
	if isinstance(dataprovider_config, dict):
		loggable["dataprovider"] = dict(dataprovider_config)
		if "api_key_b64" in loggable["dataprovider"]:
			loggable["dataprovider"]["api_key_b64"] = "<redacted>"
	return loggable


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
	start = datetime(year, month, 1, tzinfo=timezone.utc)
	if month == 12:
		end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
	else:
		end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
	return start, end


def _provider_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
	records = []
	for datetime_value, record in payload.items():
		if not isinstance(record, dict):
			raise ValueError("provider records must be objects")
		converted = dict(record)
		converted["date"] = converted.pop("datetime", datetime_value)
		converted["low"] = float(converted["low"])
		converted["high"] = float(converted["high"])
		converted["open"] = float(converted["open"])
		converted["close"] = float(converted["close"])
		converted["volume"] = int(float(converted["volume"]))
		records.append(converted)
	return records


async def process_pending_month(
	connector: TickerplantConnector,
	aggregator: Aggregator,
	symbol: str,
	year: int,
	month: int,
) -> bool:
	start, end = _month_bounds(year, month)
	intervals = aggregator.split_query((symbol, start, end))
	aggregator.queue.extend(intervals)
	worker_queue_logger.info("added %d queue elements symbol=%s", len(intervals), symbol)

	records: list[dict[str, Any]] = []
	while aggregator.queue:
		payloads = await aggregator.consume_batch()
		if any(payload is None for payload in payloads):
			return False
		for payload in payloads:
			if payload:
				records.extend(_provider_records(payload))

	try:
		connector.data({symbol: records})
		worker_queue_logger.info("pushed data to tickerplant symbol=%s records=%d", symbol, len(records))
		connector.setdone(symbol, year, month)
	except Exception:
		worker_queue_logger.critical(
			"failed to push data to tickerplant symbol=%s year=%d month=%d",
			symbol,
			year,
			month,
		)
		raise
	return True


async def poll_once(
	config: dict[str, Any],
	connector: TickerplantConnector | None = None,
	aggregator: Aggregator | None = None,
) -> None:
	tickerplant_config = config.get("tickerplant", {})
	if not isinstance(tickerplant_config, dict):
		raise ValueError("configuration['tickerplant'] must be a mapping")

	connector = connector or TickerplantConnector(
		str(tickerplant_config.get("url", "http://localhost:8000"))
	)
	aggregator = aggregator or Aggregator(config)
	start = str(config.get("start", "1970-01-01T00:00:00Z"))
	end = str(config.get("end", datetime.now(timezone.utc).isoformat()))
	configured_symbols = config.get("symbols", [])
	if not isinstance(configured_symbols, list):
		raise ValueError("configuration['symbols'] must be a list")
	allowed_symbols = {str(symbol) for symbol in configured_symbols}

	pending = connector.getpending(start, end)
	for entry in pending:
		symbol = str(entry["symbol"])
		if allowed_symbols and symbol not in allowed_symbols:
			continue
		await process_pending_month(
			connector,
			aggregator,
			symbol,
			int(entry["year"]),
			int(entry["month"]),
		)


async def _poll_loop(config: dict[str, Any]) -> None:
	connector = TickerplantConnector(config.get("tickerplant", {}).get("url", "http://localhost:8000"))
	aggregator = Aggregator(config)
	while True:
		try:
			await poll_once(config, connector, aggregator)
		except Exception:
			pass
		await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def lifespan(_: FastAPI):
	configure_logging()
	config = load_config()
	config_logger.info("loaded configuration path=%s config=%s", CONFIG_PATH, _loggable_config(config))
	task = asyncio.create_task(_poll_loop(config))
	try:
		yield
	finally:
		task.cancel()
		await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Dataprovider", lifespan=lifespan)
