# app/pipeline.py
import logging
from hashlib import sha256

from app import config, storage
from app.detector.detector import detect
from app.domain import Candidate, DetectionResult, DownloadedImage, PipelineResult
from app.downloader.downloader import download
from app.ranking.ranking import count_at_or_above_threshold, rank
from app.search.search import search

logger = logging.getLogger(__name__)


def run(keyword: str, count: int) -> PipelineResult:
    if count < 1:
        raise ValueError(f"count pozitif olmalı, alınan: {count}")
    if count > config.MAX_COUNT:
        raise ValueError(f"count en fazla {config.MAX_COUNT} olabilir, alınan: {count}")

    fetch_count = int(count * config.OVERFETCH)
    candidates: list[Candidate] = search(keyword, fetch_count)

    # Adaylar TOPLU verilir: download([candidate]) biçiminde tek tek çağırmak
    # MAX_CONCURRENT_DOWNLOADS işçilik havuza her seferinde 1 iş düşürür ve
    # eşzamanlılığın süre kazancı hiç görünmez (§5 pipeline sözleşmesi).
    downloaded = download(candidates)

    seen_hashes: set[bytes] = set()
    unique_downloaded: list[DownloadedImage] = []
    for image in downloaded:
        content_hash = sha256(image.data).digest()
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        unique_downloaded.append(image)

    results: list[DetectionResult] = [
        detect(image, keyword) for image in unique_downloaded
    ]
    raw_threshold_count = count_at_or_above_threshold(
        results,
        config.DETECT_THRESHOLD,
    )

    ranked = rank(
        results,
        config.DETECT_THRESHOLD,
        count,
    )

    # Tek satır, KOŞULSUZ: eşiği gerçek sonuçlara bakarak ayarlamanın (Karar 5) ve
    # "0 bulundu" teşhisinin (§6) dayanağı bu sayıların YAN YANA olması. Eşzamanlı
    # isteklerde hangi satır hangi aramaya ait olduğu için keyword de basılır.
    logger.info(
        "Arama özeti keyword=%r istenen=%d aday=%d inen=%d tekil=%d esigi_gecen=%d",
        keyword,
        count,
        len(candidates),
        len(downloaded),
        len(unique_downloaded),
        raw_threshold_count,
    )

    saved_images = [storage.save_image(image) for image in ranked]

    return PipelineResult(
        images=saved_images,
        requested=count,
        found=len(saved_images),
    )
