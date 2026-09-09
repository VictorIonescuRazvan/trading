CREATE TABLE IF NOT EXISTS symbols (
    symbol TEXT NOT NULL,
    date INTEGER NOT NULL,
    low REAL NOT NULL,
    high REAL NOT NULL,
    open REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_symbols_symbol
    ON symbols(symbol);
