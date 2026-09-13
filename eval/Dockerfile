FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY packages ./packages
COPY README.md ./
RUN uv sync --frozen --no-dev

EXPOSE 5001

CMD ["uv", "run", "fastapi", "run", "--host", "0.0.0.0", "--port", "5001"]