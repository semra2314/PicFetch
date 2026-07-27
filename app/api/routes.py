from fastapi import APIRouter, HTTPException
from app import pipeline
from app.api.schemas import SearchRequest, SearchResponse, ImageResult
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/search")
def search(request: SearchRequest) -> SearchResponse:
    try:
        result = pipeline.run(request.keyword, request.count)
    except Exception as e:
        logger.exception(f"pipeline hatası keyword: {request.keyword} | {e} ")
        raise HTTPException(500, detail="Beklenmeyen bir hata oluştu") from None

    image_results = [ImageResult(source_url=img.url) for img in result.images]
    return SearchResponse(
        images=image_results, requested=result.requested, found=result.found
    )
