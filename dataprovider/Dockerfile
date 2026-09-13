FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY packages ./packages
COPY README.md ./
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "dataprovider"]
