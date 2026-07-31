import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app import config, pipeline
from app.api.schemas import HealthResponse, ImageResult, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_static_url(image_path: str | None) -> str:
    if image_path is None:
        raise RuntimeError("Pipeline sonucu dosya yolu taşımıyor.")

    downloads_dir = Path(config.DOWNLOADS_DIR).resolve()
    resolved_image_path = Path(image_path).resolve()

    try:
        relative_path = resolved_image_path.relative_to(downloads_dir)
    except ValueError as error:
        raise RuntimeError(
            "Pipeline sonucu downloads dizininin dışında bir yol taşıyor."
        ) from error

    return f"/static/{relative_path.as_posix()}"


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", max_count=config.MAX_COUNT)


@router.post("/search")
def search(request: SearchRequest) -> SearchResponse:
    try:
        result = pipeline.run(request.keyword, request.count)
    except ValueError as error:
        logger.warning(
            "Geçersiz istek keyword=%s count=%s: %s",
            request.keyword,
            request.count,
            error,
        )
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from None
    except Exception:
        logger.exception(
            "Pipeline hatası keyword=%s count=%s",
            request.keyword,
            request.count,
        )
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir hata oluştu",
        ) from None

    try:
        image_results = [
            ImageResult(
                image_url=_to_static_url(image.path),
                source_url=image.url,
            )
            for image in result.images
        ]

        return SearchResponse(
            images=image_results,
            requested=result.requested,
            found=result.found,
        )
    except Exception:
        logger.exception(
            "API yanıtı oluşturulamadı keyword=%s count=%s",
            request.keyword,
            request.count,
        )
        raise HTTPException(
            status_code=500,
            detail="Beklenmeyen bir hata oluştu",
        ) from None
