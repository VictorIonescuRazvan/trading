CREATE TABLE IF NOT EXISTS symbolMetadata (
    symbol TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    status INTEGER NOT NULL CHECK (status IN (0, 1)),
    PRIMARY KEY (symbol, year, month)
);

CREATE INDEX IF NOT EXISTS idx_symbolMetadata_symbol_year_month
    ON symbolMetadata(symbol, year, month);
