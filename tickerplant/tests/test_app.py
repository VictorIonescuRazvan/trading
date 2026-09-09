import pytest

from app import is_valid_stock_ticker
from tickerplant.api import MetadataEntry


@pytest.mark.parametrize(
    "symbol",
    [
        "AAPL",
        "MSFT",
        "BRK.B",
        "aapl",
        "X1",
        "ABC123",
    ],
)
def test_valid_stock_tickers(symbol):
    assert is_valid_stock_ticker(symbol) is True


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "AAPL123",
        "BRK-B",
        "AAPL!",
        "éclair",
        " AAPL",
        "AAPL ",
        "TESTING",
        "NONE",
        "None",
        "1234567",
        "ABC/DEF",
        "abc def",
    ],
)
def test_invalid_stock_tickers(symbol):
    assert is_valid_stock_ticker(symbol) is False


@pytest.mark.parametrize(
    "symbol",
    [
        "AAPL",
        "BRK.B",
        "X1",
        "abc123",
    ],
)
def test_metadata_entry_accepts_valid_tickers(symbol):
    entry = MetadataEntry(symbol=symbol, year=2024, month=1)
    assert entry.symbol == symbol


@pytest.mark.parametrize(
    "symbol",
    [
        "",
        "AAPL123",
        "AAPL!",
        "AAPL ",
        "NONE",
        "1234567",
    ],
)
def test_metadata_entry_rejects_invalid_tickers(symbol):
    with pytest.raises(ValueError):
        MetadataEntry(symbol=symbol, year=2024, month=1)
