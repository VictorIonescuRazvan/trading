import logging

import pytest

from dataprovider import logging_config


def test_formatter_uses_documented_format() -> None:
    record = logging.LogRecord(
        name="dataprovider.worker_queue",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="public API rate limit symbol=%s",
        args=("AAPL",),
        exc_info=None,
    )
    record.funcName = "test_formatter_uses_documented_format"

    formatted = logging_config.DataproviderFormatter().format(record)

    assert "dataprovider-error(3)-test_formatter_uses_documented_format: " in formatted
    assert formatted.endswith("public API rate limit symbol=AAPL")


def test_configure_logging_fails_with_stdout_when_directory_is_unusable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(logging_config, "LOG_DIR", logging_config.Path("/missing/dataprovider"))

    with pytest.raises(RuntimeError, match="log directory is not usable"):
        logging_config.configure_logging()

    assert "dataprovider logging initialization failed" in capsys.readouterr().out