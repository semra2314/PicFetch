# app/pipeline.py
import logging
from app.config import OVERFETCH, DETECT_THRESHOLD
from app.domain import Candidate, DownloadedImage, DetectionResult, PipelineResult
from app.search.search import search
from app.downloader.downloader import download
from app.detector.detector import detect
from app.ranking.ranking import rank

logger = logging.getLogger(__name__)


def run(keyword: str, count: int) -> PipelineResult:
    if count < 1:
        raise ValueError(f"count pozitif olmalı, alınan: {count}")
    fetch_count = int(count * OVERFETCH)
    candidates: list[Candidate] = search(keyword, fetch_count)
    results: list[DetectionResult] = []
    for candidate in candidates:
        downloaded = download([candidate])
        if not downloaded:
            logger.warning("İndirme başarısız, atlanıyor: %s", candidate.url)
            continue
        image = downloaded[0]
        try:
            result = detect(image, keyword)
        except Exception:
            logger.exception("Tespit başarısız, atlanıyor: %s", image.url)
            continue
        results.append(result)
    ranked = rank(results,DETECT_THRESHOLD,count)
    
    if len(ranked) < count:
        logger.info("Yetersiz sonuç: %d istendi, %d bulundu", count, len(ranked))
        
    return PipelineResult(images=ranked, requested=count, found=len(ranked))
        
