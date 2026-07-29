from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app import config
from app.logging_setup import setup_logging
from app.api.routes import router

setup_logging()

app = FastAPI()
app.include_router(router)
app.mount("/static", StaticFiles(directory=config.DOWNLOADS_DIR), name="static")