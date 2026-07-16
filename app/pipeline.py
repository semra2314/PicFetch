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

    # 2. Madde Çözümü: Tüm adayları tek seferde/toplu olarak indiriyoruz
    downloaded_images = download(candidates)
    if not downloaded_images:
        logger.warning("Adayların hiçbiri indirilemedi, keyword: %s", keyword)
        return []

    results = []
    for image in downloaded_images:
        # 1. Madde Çözümü: detect() artık None dönmediği için 'if result is None' kontrolü kaldırıldı.
        # Güven skoru (confidence) düşük olsa bile rank() fonksiyonunda DETECT_THRESHOLD ile elenecek.
        result = detect(image, keyword)
        results.append(result)

    logger.info("toplam aday sayısı: %d, toplam sonuç sayısı: %d", len(candidates), len(results))
    
    ranked = rank(results, DETECT_THRESHOLD, count)
    if not ranked:
        logger.warning("Sıralama sonrası hiç sonuç kalmadı (eşik: %s)", DETECT_THRESHOLD)
        
    return ranked