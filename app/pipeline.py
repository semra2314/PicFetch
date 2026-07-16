from app.domain import DownloadedImage, Candidate, DetectionResult
from app.search.search import search
from app.detector.detector import detect
from app.downloader.downloader import download
from app.ranking.ranking import rank
from app.config import OVERFETCH, DETECT_THRESHOLD
from app.logging_setup import setup_logging
import logging

logger = logging.getLogger(__name__)

def run(keyword: str, count: int) -> list[DownloadedImage]:
    candidates = search(keyword, count * OVERFETCH)
    if not candidates:
        logger.warning("Arama sonucu boş döndü, keyword: %s", keyword)
        return []

    results = []
    for candidate in candidates:
        downloaded = download([candidate])
        if not downloaded:
            logger.warning("Aday indirilemedi: %s", candidate.url)
            continue
        image = downloaded[0]

        result = detect(image, keyword)
        if result is None:
            logger.warning("Tespit başarısız, görsel atlandı: %s", image.url)
            continue
        results.append(result)

    logger.info("toplam aday sayısı: %d, toplam sonuç sayısı: %d", len(candidates), len(results))

    ranked = rank(results, DETECT_THRESHOLD, count)
    if not ranked:
        logger.warning("Sıralama sonrası hiç sonuç kalmadı (eşik: %s)", DETECT_THRESHOLD)
    return ranked
