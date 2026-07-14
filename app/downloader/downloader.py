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
        success = False  # Bu URL için henüz başarılı olmadık
        # config.DOWNLOAD_RETRIES 2 ise, range(3) bize 0, 1, 2 verir (Toplam 3 deneme)
        for attempt in range(config.DOWNLOAD_RETRIES + 1):
            try:
                response = requests.get(candidate.url, timeout= config.DOWNLOAD_TIMEOUT) # requests.get(): Seçtiği URL'ye HTTP GET isteği atar.
            # response:requests.get() fonksiyonunun döndürdüğü HTTP yanıt nesnesidir. Bu nesne içinde görselin verisi, boyutu, yükleme durumu (status) gibi birçok bilgi bulunur.

                # 1. Kontrol: Gerçekten görsel mi?
                content_type = response.headers.get('Content-Type', '')
            # content_type: Yanıttan gelen Content-Type başlığını alır (Örn: "image/jpeg"). Eğer başlık yoksa boş string döner.
            
                if not content_type.startswith('image/'):
                # content_type.startswith('image/'): Eğer 'content_type' stringi 'image/' ile başlamıyorsa (yani görsel değilse) doğru (True) döner.
                    logging.warning(f"\n URL görsel değil: {candidate.url} - İçerik tipi: {content_type}")
                # logging.warning(...): Eğer görsel değilse, bir uyarı mesajı kaydeder.
                    break  # Görsel değilse tekrar denemenin anlamı yok, döngüden çık.

                # continue: Bu satır, döngünün geri kalanını (yani indir ve listeye ekle kısmını) bu aday için çalıştırmaz ve bir sonraki adaya geçer.
                # continue  # Bu URL'yi atla, bir sonrakine geç
        
                # 2. Başarılı! Veriyi al ve listeye ekle.

                bytes_data = response.content # content: Yanıttan gelen ham binary veriyi (bayt dizisi) alır.

                image = DownloadedImage(url=candidate.url, data=bytes_data) # DownloadedImage: İndirilen görselin URL'sini ve raw içeriğini tutan yapıyı oluşturur.

                downloaded_images.append(image) # append: Bu yeni oluşturulan 'image' nesnesini, 'downloaded_images' listesine ekler.
                success = True  # Başardık!
                break  # Başarılı olduğumuz için retry döngüsünden çık, bir sonraki URL'ye geç.

            except Exception as e:
            # Hata oldu. Kaçıncı deneme olduğumuzu loglayalım.
                logging.warning(f"İndirme hatası (Deneme {attempt + 1}/{config.DOWNLOAD_RETRIES + 1}): {candidate.url} - Hata: {e}")
            # Burada 'break' YOK. Döngü devam eder ve bir sonraki 'attempt' denemesini yapar.

    return downloaded_images # return: Tüm döngü bittikten sonra, içinde indirilen tüm görsellerin bulunduğu listeyi geri döndürür.




""" 
range(config.DOWNLOAD_RETRIES + 1): Eğer config'de retry 2 ise, +1 ekleyerek toplam 3 deneme (1 ilk deneme + 2 retry) hakkımız olur.
İçerik tipi hatalıysa (break) veya indirme başarılıysa (break), for attempt döngüsünden erken çıkıyoruz. Çünkü başarısız bir HTML sayfasını 3 kez indirmeye çalışmak zaman israfıdır.
Sadece except bloğunda (ağ hatası, timeout) break yoktur. Bu sayede döngü bir sonraki denemeye devam eder.
"""