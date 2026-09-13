import asyncio

from .app import app
from .app import run_worker


def main() -> None:
    asyncio.run(run_worker())


__all__ = ["app", "main"]
