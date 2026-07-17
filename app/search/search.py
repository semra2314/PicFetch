import time
import logging
from ddgs import DDGS
from app.domain import Candidate
from app.config import SEARCH_RETRIES, SEARCH_RETRY_DELAY

logger = logging.getLogger(
    __name__
)  # __name__ logun search modülünden geldiğini göstermek için kullanılır


def search(keyword: str, count: int) -> list[Candidate]:
    """Verilen arama kelimesiyle DuckDuckGo üzerinden görsel araması yapar
    ve belirlenen sayıda Candidate nesnesi döndürür."""

    for attempt in range(SEARCH_RETRIES):
        candidates = []  # her deneme için temiz arama yap,diğer arama sonuçlarıyla karışmaması için

        try:
            results = DDGS().images(
                query=keyword, max_results=count
            )  # sonuç görselini ddgs kütüphanesi ile arar
            if not results:  # sonucun arandığı ama sonucun 0 olduğu durum
                logger.warning(
                    f"{keyword} için 0 sonuç bulundu"
                )  # kritik durum değil ama uyarı alıyoruz(warning)
                return []

            for result in (
                results
            ):  # her bir sonuç için candidate(aday nesne )oluşturup listeledik
                url = result.get("image")
                if not url:
                    logger.warning("eksik anahtarlı sonuç atlandı")
                    continue  # image yoksa bu turu atlayıp devam eder
                candidate = Candidate(url=url)
                candidates.append(candidate)

                if len(candidates) >= count:
                    break

            return candidates  # sonuc 0 değilse aday nesneleri döndür

        except Exception:
            logger.exception(f"Search attempt {attempt + 1} failed")
            time.sleep(SEARCH_RETRY_DELAY)
            # bir sonraki deneme için
            # configden gelen süre kadar bekler(backoff)
    return []  # tüm denemeler bitti, hiçbiri başarılı olmadı: boş dön
