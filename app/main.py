from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.api.routes import router
from app.logging_setup import setup_logging

setup_logging()

downloads_dir = Path(config.DOWNLOADS_DIR)
downloads_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.include_router(router)
app.mount("/static", StaticFiles(directory=downloads_dir), name="static")
