# app/pipeline.py
import logging

from app import config
from app.detector.detector import detect
from app.domain import Candidate, DetectionResult, PipelineResult
from app.downloader.downloader import download
from app.ranking.ranking import rank
from app.search.search import search

logger = logging.getLogger(__name__)


def run(keyword: str, count: int) -> PipelineResult:
    if count < 1:
        raise ValueError(f"count pozitif olmalı, alınan: {count}")
    if count > config.MAX_COUNT:
        raise ValueError(f"count en fazla {config.MAX_COUNT} olabilir, alınan: {count}")
    fetch_count = int(count * config.OVERFETCH)
    candidates: list[Candidate] = search(keyword, fetch_count)

    downloaded = download(candidates)

    results: list[DetectionResult] = []
    for image in downloaded:
        result = detect(image, keyword)
        results.append(result)

    ranked = rank(results, config.DETECT_THRESHOLD, count)

    logger.info(
        "Aday: %d, İndirilen: %d, Eşiği geçen: %d",
        len(candidates),
        len(downloaded),
        len(ranked),
    )

    if len(ranked) < count:
        logger.info("Yetersiz sonuç: %d istendi, %d bulundu", count, len(ranked))

    return PipelineResult(images=ranked, requested=count, found=len(ranked))
