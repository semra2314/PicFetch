import time
import random
import logging
from typing import Any

from ddgs import DDGS

from app.domain import Candidate
from app import config

logger = logging.getLogger(
    __name__
)  # __name__ logun search modülünden geldiğini göstermek için kullanılır


def _fetch_page(
    keyword: str,
    count: int,
    page: int,
    min_delay: int,
    max_delay: int,
) -> list[dict[str, Any]]:
    """Tek bir sonuç sayfasını çeker; tüm denemeler başarısızsa boş liste döner.

    Retry bilinçli olarak SAYFA BAŞINA çalışır. Tüm aramayı sarsaydı, 3. sayfada
    alınan geçici bir hata 1. ve 2. sayfadan toplanmış adayları da çöpe atardı.
    """
    for attempt in range(config.SEARCH_RETRIES):
        try:
            with DDGS() as ddgs:
                return ddgs.images(
                    query=keyword,
                    max_results=count,
                    page=page,
                    backend=config.SEARCH_BACKEND,
                )  # sonuç görselini ddgs kütüphanesi ile arar
        except Exception:
            logger.exception(f"Search attempt {attempt + 1} failed (sayfa {page})")
            if attempt < config.SEARCH_RETRIES - 1:
                delay = random.randint(min_delay, max_delay)
                time.sleep(delay)
                # bir sonraki deneme için
                # configden gelen aralıktan gelen rastgele süre kadar bekler(backoff)
    return []


def search(keyword: str, count: int) -> list[Candidate]:
    """Verilen arama kelimesiyle görsel araması yapar ve en fazla `count`
    adet Candidate döndürür.

    Sayfalama zorunlu: ddgs, `max_results`'ı motora hiç iletmiyor (yalnızca
    dönen listeyi kırpıyor), bu yüzden Bing'e sayfa başına sabit 35 sonuç
    sorulur. Tek çağrıyla count'a ulaşmak mümkün değil — ayrıntı için
    config.SEARCH_MAX_PAGES yorumuna bakın.
    """

    # Config'de min > max olarak yanlış girilmişse bile sistemi çökertmeyip sessizce düzeltiyoruz
    min_range = min(config.SEARCH_RETRY_DELAY_MIN, config.SEARCH_RETRY_DELAY_MAX)
    max_range = max(config.SEARCH_RETRY_DELAY_MIN, config.SEARCH_RETRY_DELAY_MAX)

    candidates: list[Candidate] = []
    seen_urls: set[str] = set()

    for page in range(1, config.SEARCH_MAX_PAGES + 1):
        results = _fetch_page(keyword, count, page, min_range, max_range)
        if not results:
            break  # sayfa boş ya da tüm denemeler tükendi: sonraki sayfayı istemenin anlamı yok

        # URL bazlı tekilleştirme. pipeline zaten içerik hash'iyle tekilleştiriyor
        # ama o İNDİRDİKTEN sonra çalışıyor; burada elenen her tekrar, hiç
        # yapılmayan bir HTTP isteği demek.
        new_on_page = 0
        for (
            result
        ) in results:  # her bir sonuç için candidate(aday nesne )oluşturup listeledik
            url = result.get("image")
            if not url:
                logger.warning("eksik anahtarlı sonuç atlandı")
                continue  # image yoksa bu turu atlayıp devam eder
            if url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(Candidate(url=url))
            new_on_page += 1

            if len(candidates) >= count:
                return candidates

        if new_on_page == 0:
            # Sayfa tamamen tekrardan ibaret: kaynak tükenmiş. SEARCH_MAX_PAGES'e
            # kadar devam etmek boşuna istek atmak olur.
            logger.info(
                "Sayfa %d yeni sonuç getirmedi, sayfalama durduruldu (aday=%d)",
                page,
                len(candidates),
            )
            break

    if not candidates:
        logger.warning(
            f"{keyword} için 0 sonuç bulundu"
        )  # kritik durum değil ama uyarı alıyoruz(warning)

    return candidates
