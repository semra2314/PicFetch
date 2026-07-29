from fastapi import APIRouter, HTTPException
from app import pipeline
from app.api.schemas import SearchRequest, SearchResponse, ImageResult
import logging
from pathlib import Path
from app import config

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search")
def search(request: SearchRequest) -> SearchResponse:
    try:
        result = pipeline.run(request.keyword, request.count)
    except ValueError as e:
        logger.warning("Geçersiz istek keyword=%s count=%s: %s", request.keyword, request.count, e)
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        logger.exception(
            "Pipeline hatası keyword=%s",request.keyword, exc_info=e)
        raise HTTPException(500, detail="Beklenmeyen bir hata oluştu") from None

    image_results = [
        ImageResult(
            source_url=img.url,
            image_url=f"/static/{Path(img.path).relative_to(config.DOWNLOADS_DIR)}" if img.path else None,
        )
        for img in result.images
    ]
    return SearchResponse(
        images=image_results, requested=result.requested, found=result.found
    )
