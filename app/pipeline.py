# app/pipeline.py
import logging

from app import config, storage
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
    results: list[DetectionResult] = []

    for candidate in candidates:
        downloaded = download([candidate])
        if not downloaded:
            logger.warning(
                "İndirme başarısız, atlanıyor: %s",
                candidate.url,
            )
            continue

        image = downloaded[0]
        result = detect(image, keyword)
        results.append(result)

    ranked = rank(
        results,
        config.DETECT_THRESHOLD,
        count,
    )

    saved_images = [storage.save_image(image) for image in ranked]

    if len(saved_images) < count:
        logger.info(
            "Yetersiz sonuç: %d istendi, %d bulundu",
            count,
            len(saved_images),
        )

    return PipelineResult(
        images=saved_images,
        requested=count,
        found=len(saved_images),
    )
