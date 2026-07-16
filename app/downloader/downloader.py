import logging # bu satırın amacı logging: Hata olduğunda print yerine profesyonelce log kaydı tutmak için (Proje kuralı #5).
import requests # bu satır requests: HTTP(Internet) üzerinden veri (Resim/URL) çekmek için kullanılan kütüphane.

from app.domain import Candidate, DownloadedImage # Modüller arası konuşmamızı sağlayan ortak veri tipleri:Candidate: İndirilecek görsel adayı (URL + Source). DownloadedImage: Başarılı indirme sonrası oluşan veri (Binary içerik + Tür).
from app import config # Proje kuralı #7). Bu dosyanın "Hız Limiti" (Delay) gibi ayarlarını buradan okuruz.
# config: Timeout ve retry gibi ayarları tek bir yerden (config.py) okumak için.

def download(candidates: list[Candidate]) -> list[DownloadedImage]:
    """Her URL'yi indirir. İndirilemeyeni/gerçek görsel olmayanı ELER (listeye koymaz, LOGLAR).
    Yani dönen liste, girdiden kısa olabilir. Timeout ve retry sayısı config'ten gelir."""
    downloaded_images = []

    # İnternet varsa ve URL geçerliyse, görseli indirip listeye ekliyor.
    # eğer requests.get(candidate.url) satırında bir sorun olursa (örneğin URL bozuksa veya internet anlık koparsa), programın tamamı çöker (ConnectionError veya Timeout hatası fırlatır). Bizim istediğimiz ise o URL'yi atlayıp bir sonrakine geçmesi.
    for candidate in candidates:    # bu döngü, dışarıdan gelen aday listesini baştan sona gezer. ve sırayla her birini işler.
        # config.DOWNLOAD_RETRIES 2 ise, range(3) bize 0, 1, 2 verir (Toplam 3 deneme)
        for attempt in range(config.DOWNLOAD_RETRIES + 1):
            try:
                # stream=True: İsteği açar ancak gövdeyi (body) hemen indirmez, sadece header'ları çeker.
                response = requests.get(candidate.url, stream=True, timeout=config.DOWNLOAD_TIMEOUT)

                # 1. Kontrol: HTTP durum kodu başarılı mı? (Örn: 404, 403 vb. durumları logda ayrıştırmak için)
                if response.status_code != 200:
                    logging.warning(f"İstek başarısız (Durum kodu: {response.status_code}): {candidate.url}")
                    if response.status_code in [400, 401, 403, 404, 410]:
                        break  # İstemci hatalarında tekrar denemeye gerek yok, döngüden çık.
                    response.raise_for_status()  # Sunucu hatalarında (5xx) exception fırlatarak retry yapılmasını sağla.

                # 2. Kontrol: Gerçekten görsel mi?
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    logging.warning(f"URL görsel değil: {candidate.url} - İçerik tipi: {content_type} (Durum kodu: {response.status_code})")
                    break  # Görsel değilse tekrar denemenin anlamı yok, döngüden çık.

                # 3. Kontrol: Boyut kontrolü (Content-Length varsa kontrol et)
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) > config.MAX_FILE_SIZE:
                    size_mb = int(content_length) / (1024 * 1024)
                    logging.warning(f"Dosya çok büyük: {candidate.url} - Boyut: {size_mb:.2f} MB (Max: {config.MAX_FILE_SIZE / (1024 * 1024)} MB)")
                    break  # Büyük dosyayı tekrar tekrar denemenin anlamı yok

                # 4. Dinamik Boyut Kontrolü & Parça Parça İndirme
                # Sunucu Content-Length başlığı göndermese bile veriyi indirirken boyutu sınırlar.
                bytes_data = bytearray()
                exceeded = False
                for chunk in response.iter_content(chunk_size=128 * 1024):  # 128 KB'lık parçalar halinde oku
                    if chunk:
                        bytes_data.extend(chunk)
                        if len(bytes_data) > config.MAX_FILE_SIZE:
                            size_mb = len(bytes_data) / (1024 * 1024)
                            logging.warning(f"Dosya indirilirken sınır aşıldı: {candidate.url} - Aşım Boyutu: {size_mb:.2f} MB (Max: {config.MAX_FILE_SIZE / (1024 * 1024)} MB)")
                            exceeded = True
                            break
                
                if exceeded:
                    break  # Sınır aşıldığı için döngüden çık ve bu adayı atla

                # 5. Başarılı! Veriyi al ve listeye ekle.
                image = DownloadedImage(url=candidate.url, data=bytes(bytes_data))
                downloaded_images.append(image)
                break  # Başarılı olduğumuz için retry döngüsünden çık, bir sonraki URL'ye geç.

            except Exception as e:
                # Hata oldu. Kaçıncı deneme olduğumuzu loglayalım.
                logging.warning(f"İndirme hatası (Deneme {attempt + 1}/{config.DOWNLOAD_RETRIES + 1}): {candidate.url} - Hata: {e}")
                # Burada 'break' YOK. Döngü devam eder ve bir sonraki 'attempt' denemesini yapar.

    # Toplu özet logu
    logging.info(f"İndirme işlemi tamamlandı. Toplam aday: {len(candidates)}, Başarılı: {len(downloaded_images)}")
    return downloaded_images

""" 
range(config.DOWNLOAD_RETRIES + 1): Eğer config'de retry 2 ise, +1 ekleyerek toplam 3 deneme (1 ilk deneme + 2 retry) hakkımız olur.
İçerik tipi hatalıysa (break) veya indirme başarılıysa (break), for attempt döngüsünden erken çıkıyoruz. Çünkü başarısız bir HTML sayfasını 3 kez indirmeye çalışmak zaman israfıdır.
Sadece except bloğunda (ağ hatası, timeout) break yoktur. Bu sayede döngü bir sonraki denemeye devam eder.
"""
