from fastapi import FastAPI
from app.logging_setup import setup_logging
from app.api.routes import router

setup_logging()

app = FastAPI()
app.include_router(router)
