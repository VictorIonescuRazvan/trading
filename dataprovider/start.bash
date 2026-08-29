#!/bin/bash
uv sync --link-mode=copy
uv run uvicorn dataprovider.app:app --app-dir src --reload
