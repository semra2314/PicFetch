import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.api.routes import router
from app.detector.detector import warm_up
from app.logging_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

downloads_dir = Path(config.DOWNLOADS_DIR)
downloads_dir.mkdir(parents=True, exist_ok=True)

frontend_dist = Path(config.FRONTEND_DIST)
frontend_assets = frontend_dist / "assets"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    warm_up()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)

# İndirilen ve doğrulanan görseller yalnızca /static altında sunulur.
app.mount(
    "/static",
    StaticFiles(directory=downloads_dir),
    name="static",
)

# Vite tarafından üretilen CSS ve JavaScript dosyaları ayrı bir
# isim alanında tutulur; /static ile çakışmaz.
#
# Mount koşulsuz kurulur. Koşullu olsaydı en sık karşılaşılan sıra
# bozulurdu: sunucu çalışırken 'pnpm build' alındığında / adresi 200
# döner (yol her istekte okunuyor) ama CSS/JS 404 verir ve kullanıcı
# hiçbir hata mesajı olmayan bir beyaz sayfa görür. --reload de
# tetiklenmez, çünkü değişen dosyalar Python değil.
#
# check_dir=False: klasör henüz yokken StaticFiles'ın açılışta hata
# vermesini engeller. Dosya bulunamadığında normal 404 döner.
app.mount(
    "/assets",
    StaticFiles(directory=frontend_assets, check_dir=False),
    name="assets",
)

if not frontend_assets.is_dir():
    logger.warning(
        "Frontend build bulunamadı: %s. "
        "Arayüz için 'cd frontend && pnpm build' çalıştırın.",
        frontend_assets,
    )


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    # index.html yolu modül yüklenirken değil, her istekte config'den okunur.
    # Sebebi: testler config.FRONTEND_DIST'i geçici bir dizine yönlendirip
    # hem "build var" (200) hem "build yok" (503) durumunu doğrulayabilsin.
    frontend_index = Path(config.FRONTEND_DIST) / "index.html"

    if not frontend_index.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend build edilmemiş. 'cd frontend && pnpm build' çalıştırın."
            ),
        )

    return FileResponse(frontend_index)
