# Tickerplant Project Structure Decisions

This document records the structural and operational decisions for the tickerplant service.

## 1. Repository and package layout

- The repository root is the `tickerplant` project directory.
- Application Python code lives in `src/tickerplant/` and is imported as the `tickerplant` package.
- `pyproject.toml` is the project and dependency definition used by `uv`.
- `app.py` at the repository root contains the small standalone ticker validation helper used by the existing tests. It is not the FastAPI application entrypoint.
- `tests/` contains the pytest suite for API models, database initialization, metadata behavior, and data queries.
- `example/` contains usage examples and is not part of application startup.

## 2. FastAPI entrypoint

- The FastAPI application is the `app` object in `tickerplant.api`.
- The canonical entrypoint is declared in `pyproject.toml` as:

  ```text
  tickerplant.api:app
  ```

- Start development mode from the repository root with:

  ```bash
  uv run fastapi dev
  ```

- Start production-style serving with:

  ```bash
  uv run fastapi run
  ```

- The application initializes its database during FastAPI startup before serving requests.

## 3. Configuration and runtime storage

- Runtime configuration is read from `/etc/tickerplant/config.yaml`.
- The repository `config.yaml` documents the expected configuration values and can be copied to the system configuration location during installation.
- `db_file` selects the SQLite database path. Relative database paths are resolved relative to `/etc/tickerplant/config.yaml`.
- The current configuration uses `/var/tickerplant/db.sql`.
- Runtime configuration and database files are outside the source tree so deployments can keep code, configuration, and mutable data separate.
- The database parent directory is created by database initialization when needed.

## 4. Database schema ownership

- The SQL files in `schemas/` are the single source of truth for the SQLite schema.
- `schemas/symbolMetadata.sql` defines the `symbolMetadata` table and its index.
- `schemas/symbols.sql` defines the `symbols` table and its index.
- Python code must execute these schema files through `init_db`; it must not duplicate their `CREATE TABLE`, index, constraint, or column definitions as SQL strings.
- Schema files are applied with SQLite `executescript`, and use `IF NOT EXISTS` so startup can safely initialize an existing database.
- Code that opens a database directly, including `Metadata`, must initialize it through the shared schema loader first.
- The API resolves the schema directory from the repository/package layout rather than from the process working directory.

## 5. Database responsibilities

- `init_db.py` owns schema application and database-file initialization.
- `dbquery.py` owns minute-level market data access through the `symbols` table.
- `metadata.py` owns completion status for symbol/year/month work through the `symbolMetadata` table.
- The API creates the database query and metadata services during startup and exposes them through HTTP endpoints.
- SQLite connections use `check_same_thread=False`; each service protects its connection with a thread lock.

## 6. API responsibilities

- `api.py` owns FastAPI setup, request models, validation, startup wiring, and HTTP error translation.
- `GET /meta` returns pending metadata months for a symbol and date range.
- `POST /data` inserts minute records grouped by symbol.
- `POST /setdone` marks a symbol/year/month metadata entry as complete.
- Request validation belongs in Pydantic models and API validation helpers; persistence validation belongs in the database service classes.
- Ticker symbols are constrained to the existing six-character, alphanumeric-or-period format and reject sentinel values such as `NONE`, `NULL`, `NAN`, and `INF`.

## 7. Testing decisions

- Tests run with `uv run pytest` from the repository root.
- Pytest is configured with both `.` and `src` on `pythonpath` so it can import the root helper and the packaged application.
- Database tests use temporary SQLite paths and the real files in `schemas/`; they should not recreate the production schema in test strings.
- Changes to schema structure should update the appropriate SQL file and the focused database tests together.
- A successful test run does not replace a startup check: the deployed config path and database path must also be available when running the FastAPI service.

## 8. Change guidelines

- Preserve the `src` package layout and the `tickerplant.api:app` entrypoint.
- Keep schema changes in `schemas/*.sql` and reuse `init_db` everywhere a database is opened.
- Keep mutable deployment files under `/etc/tickerplant` and `/var/tickerplant`; do not commit those runtime files into the source package.
- Add or update focused tests when changing API contracts, persistence behavior, or schema definitions.
- Update this document when a structural or operational decision changes.
