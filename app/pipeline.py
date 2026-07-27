# app/pipeline.py
import logging

from app.config import DETECT_THRESHOLD, MAX_COUNT, OVERFETCH
from app.detector.detector import detect
from app.domain import Candidate, DetectionResult, PipelineResult
from app.downloader.downloader import download
from app.ranking.ranking import rank
from app.search.search import search

logger = logging.getLogger(__name__)


def run(keyword: str, count: int) -> PipelineResult:
    if count < 1:
        raise ValueError(f"count pozitif olmalı, alınan: {count}")
    if count > MAX_COUNT:
        raise ValueError(
            f"count en fazla {MAX_COUNT} olabilir, alınan: {count}"
        )
    fetch_count = int(count * OVERFETCH)
    candidates: list[Candidate] = search(keyword, fetch_count)
    results: list[DetectionResult] = []
    for candidate in candidates:
        downloaded = download([candidate])
        if not downloaded:
            logger.warning("İndirme başarısız, atlanıyor: %s", candidate.url)
            continue

        image = downloaded[0]
        result = detect(image, keyword)
        results.append(result)
    ranked = rank(results, DETECT_THRESHOLD, count)

    if len(ranked) < count:
        logger.info("Yetersiz sonuç: %d istendi, %d bulundu", count, len(ranked))

    return PipelineResult(images=ranked, requested=count, found=len(ranked))
