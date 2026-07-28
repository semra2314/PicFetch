import logging  # bu satırın amacı logging: Hata olduğunda print yerine profesyonelce log kaydı tutmak için (Proje kuralı #5).
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests  # bu satır requests: HTTP(Internet) üzerinden veri (Resim/URL) çekmek için kullanılan kütüphane.

from app.domain import (
    Candidate,
    DownloadedImage,
)  # Modüller arası konuşmamızı sağlayan ortak veri tipleri: Candidate: İndirilecek görsel adayı (URL + Source). DownloadedImage: Başarılı indirme sonrası oluşan veri (Binary içerik + Tür).
from app import (
    config,
)  # Proje kuralı #7). Bu dosyanın "Hız Limiti" (Delay) gibi ayarlarını buradan okuruz.

logger = logging.getLogger(__name__)
# config: Timeout ve retry gibi ayarları tek bir yerden (config.py) okumak için.


def _download_single(candidate: Candidate) -> DownloadedImage | None:
    """Tek bir URL'yi indirir. Başarısızsa None döndürür."""
    # config.DOWNLOAD_RETRIES 2 ise, range(3) bize 0, 1, 2 verir (Toplam 3 deneme)
    for attempt in range(config.DOWNLOAD_RETRIES + 1):
        try:
            # stream=True: İsteği açar ancak gövdeyi (body) hemen indirmez, sadece header'ları çeker.
            response = requests.get(
                candidate.url, stream=True, timeout=config.DOWNLOAD_TIMEOUT
            )
            try:
                # 1. Kontrol: HTTP durum kodu başarılı mı? (Örn: 404, 403 vb. durumları logda ayrıştırmak için)
                if response.status_code != 200:
                    logger.warning(
                        f"İstek başarısız (Durum kodu: {response.status_code}): {candidate.url}"
                    )
                    if response.status_code in config.NON_RETRYABLE_STATUS_CODES:
                        break  # İstemci hatalarında tekrar denemeye gerek yok, döngüden çık.
                    response.raise_for_status()  # Sunucu hatalarında (5xx) exception fırlatarak retry yapılmasını sağla.

                # 2. Kontrol: Gerçekten görsel mi?
                content_type = response.headers.get("Content-Type", "")
                if not content_type.lower().startswith("image/"):
                    logger.warning(
                        f"URL görsel değil: {candidate.url} - İçerik tipi: {content_type} (Durum kodu: {response.status_code})"
                    )
                    break  # Görsel değilse tekrar denemenin anlamı yok, döngüden çık.

                # 3. Kontrol: Boyut kontrolü (Content-Length varsa kontrol et)
                content_length_header = response.headers.get("Content-Length")
                if (
                    content_length_header
                ):  # bu satır content_length_header None değilse kontrol eder
                    try:  # content length integer değilse(str vb.) hata fırlatır
                        content_length = int(content_length_header)
                        if content_length > config.MAX_FILE_SIZE:
                            size_mb = content_length / (1024 * 1024)
                            logger.warning(
                                f"Dosya çok büyük: {candidate.url} - Boyut: {size_mb:.2f} MB (Max: {config.MAX_FILE_SIZE / (1024 * 1024)} MB)"
                            )
                            break  # Büyük dosyayı tekrar tekrar denemenin anlamı yok

                    except (
                        ValueError,
                        TypeError,
                    ):  # burda content_length_header integer değilse(str vb.) hata fırlatır
                        logger.warning(
                            f"Geçersiz Content-Length başlığı: {content_length_header}"
                        )

                # 4. Dinamik Boyut Kontrolü & Parça Parça İndirme
                # Sunucu Content-Length başlığı göndermese bile veriyi indirirken boyutu sınırlar.
                bytes_data = bytearray()
                exceeded = False
                for chunk in response.iter_content(
                    chunk_size=config.DOWNLOAD_CHUNK_SIZE
                ):  # config'ten gelen boyutta parçalar halinde oku
                    if chunk:
                        bytes_data.extend(chunk)
                        if len(bytes_data) > config.MAX_FILE_SIZE:
                            size_mb = len(bytes_data) / (1024 * 1024)
                            logger.warning(
                                f"Dosya indirilirken sınır aşıldı: {candidate.url} - Aşım Boyutu: {size_mb:.2f} MB (Max: {config.MAX_FILE_SIZE / (1024 * 1024)} MB)"
                            )
                            exceeded = True
                            break

                if exceeded:
                    break  # Sınır aşıldığı için döngüden çık ve bu adayı atla

                if not bytes_data:
                    logger.warning(f"Görsel verisi boş (0 bayt): {candidate.url}")
                    break

                # 5. Başarılı! Veriyi al ve döndür.
                return DownloadedImage(
                    url=candidate.url,
                    data=bytes(bytes_data),
                    content_type=content_type,
                )
            finally:
                response.close()

        except requests.RequestException as e:
            # Hata oldu. Kaçıncı deneme olduğumuzu loglayalım.
            logger.warning(
                f"İndirme hatası (Deneme {attempt + 1}/{config.DOWNLOAD_RETRIES + 1}): {candidate.url} - Hata: {e}"
            )
            # Burada 'break' YOK. Döngü devam eder ve bir sonraki 'attempt' denemesini yapar.

    return None


def download(candidates: list[Candidate]) -> list[DownloadedImage]:
    """URL'leri eşzamanlı olarak indirir. İndirilemeyeni/gerçek görsel olmayanı ELER (listeye koymaz, LOGLAR).
    Yani dönen liste, girdiden kısa olabilir. Timeout ve retry sayısı config'ten gelir."""
    if not candidates:
        return []

    results_by_index = {}

    # Thread pool ile eşzamanlı indirme
    # max_workers, aynı anda bellekte tutulacak maksimum görsel sayısını (akış prensibi) sınırlar.
    with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_DOWNLOADS) as executor:
        # Tüm adaylar için görevleri başlat
        future_to_index = {
            executor.submit(_download_single, candidate): index
            for index, candidate in enumerate(candidates)
        }

        # Tamamlanan görevleri topla
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            candidate = candidates[index]
            try:
                result = future.result()
                if result is not None:
                    results_by_index[index] = result
            except Exception as e:
                logger.exception(f"Beklenmeyen hata ({candidate.url}): {e}")

    # Sonuçları orijinal sıraya göre diz
    downloaded_images = [
        results_by_index[index] for index in sorted(results_by_index.keys())
    ]

    # Toplu özet logu
    logger.info(
        f"İndirme işlemi tamamlandı. Toplam aday: {len(candidates)}, Başarılı: {len(downloaded_images)}"
    )
    return downloaded_images


""" 
range(config.DOWNLOAD_RETRIES + 1): Eğer config'de retry 2 ise, +1 ekleyerek toplam 3 deneme (1 ilk deneme + 2 retry) hakkımız olur.
İçerik tipi hatalıysa (break) veya indirme başarılıysa (break), for attempt döngüsünden erken çıkıyoruz. Çünkü başarısız bir HTML sayfasını 3 kez indirmeye çalışmak zaman israfıdır.
Sadece except bloğunda (ağ hatası, timeout) break yoktur. Bu sayede döngü bir sonraki denemeye devam eder.
"""
