from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

QUERY_LOG_PATH = Path("/var/log/tickerplant/queries.log")
REQUEST_LOG_PATH = Path("/var/log/tickerplant/requests.log")


def _sql_value(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _render_query(query: str, parameters: Iterable[Any] = ()) -> str:
    rendered = query
    for parameter in parameters:
        rendered = rendered.replace("?", _sql_value(parameter), 1)
    return " ".join(rendered.split())


def log_query(
    script_name: str,
    function_name: str,
    query: str,
    parameters: Iterable[Any] = (),
) -> None:
    _write_log(QUERY_LOG_PATH, script_name, function_name, _render_query(query, parameters))


def log_request(script_name: str, function_name: str, request: str) -> None:
    _write_log(REQUEST_LOG_PATH, script_name, function_name, request)


def _write_log(path: Path, script_name: str, function_name: str, content: str) -> None:
    line = f"{datetime.now(timezone.utc).isoformat()}: {script_name}-7-{function_name}: {content}\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as log_file:
            log_file.write(line)
    except OSError:
        pass