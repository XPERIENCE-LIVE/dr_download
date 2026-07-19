"""PyInstaller entry point for the local backend."""

import os

import uvicorn

from backend.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("DR_DOWNLOAD_PORT", "8000")))

