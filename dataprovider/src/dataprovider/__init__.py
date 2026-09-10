from .app import app


def main() -> None:
    import uvicorn

    uvicorn.run("dataprovider.app:app", host="0.0.0.0", port=8001)


__all__ = ["app", "main"]
