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

    # Adaylar TOPLU verilir: download([candidate]) biçiminde tek tek çağırmak
    # MAX_CONCURRENT_DOWNLOADS işçilik havuza her seferinde 1 iş düşürür ve
    # eşzamanlılığın süre kazancı hiç görünmez (§5 pipeline sözleşmesi).
    downloaded = download(candidates)

    results: list[DetectionResult] = [detect(image, keyword) for image in downloaded]

    ranked = rank(
        results,
        config.DETECT_THRESHOLD,
        count,
    )

    # Tek satır, KOŞULSUZ: eşiği gerçek sonuçlara bakarak ayarlamanın (Karar 5) ve
    # "0 bulundu" teşhisinin (§6) dayanağı bu sayıların YAN YANA olması. Eşzamanlı
    # isteklerde hangi satır hangi aramaya ait olduğu için keyword de basılır.
    # Bilinen sınır: esigi_gecen, rank'in count'a kırpması yüzünden min(geçen, count).
    logger.info(
        "Arama özeti keyword=%r istenen=%d aday=%d inen=%d esigi_gecen=%d",
        keyword,
        count,
        len(candidates),
        len(downloaded),
        len(ranked),
    )

    saved_images = [storage.save_image(image) for image in ranked]

    return PipelineResult(
        images=saved_images,
        requested=count,
        found=len(saved_images),
    )
