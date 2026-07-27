# bu dosyanın amacı internet sitesinden resim indirme işlemini test etmektir. ve bunu yaparken internete ihtiyaç duymaz çünkü internetten gelen verileri sahte verilerle değiştirir. yani mock kullanır.

import requests

# unittest.mock kütüphanesinden patch (fonksiyonu taklit etmek için) ve Mock (sahte nesne üretmek için) modüllerini içe aktarıyoruz.
from unittest.mock import patch, Mock

# Test edeceğimiz download fonksiyonunu ve test girdisi olarak kullanacağımız Candidate sınıfını projeden çağırıyoruz.
from app.downloader.downloader import download
from app.domain import Candidate
from app.config import DOWNLOAD_TIMEOUT


# @patch dekoratörü, requests.get fonksiyonunu geçici olarak yakalar ve yerine sahte (dublör) bir fonksiyon koyar.
# Bu sahte versiyona test fonksiyonunun argümanı olan "mock_get" adını verdik.
@patch("app.downloader.downloader.requests.get")
def test_download_success(mock_get):
    # --- 1. SAHTE CEVAP HAZIRLA (Mock/Dublör Yapılandırılması) ---
    # İstek başarılı olduğunda dönecek olan HTTP yanıtını simüle etmek için sahte bir Mock nesnesi oluşturuyoruz.
    fake_response = Mock()

    # Sunucunun başarılı döndüğünü belirtmek için HTTP Status Code'u 200 yapıyoruz.
    fake_response.status_code = 200

    # HTTP Başlıklarını (Headers) simüle ediyoruz. Görsel türünü ve boyutunu belirtiyoruz.
    fake_response.headers = {
        "Content-Type": "image/jpeg",  # downloader.py içerisindeki "image/" kontrolünden geçebilmesi için.
        "Content-Length": "5000",  # 5 KB dosya boyutu, config.MAX_FILE_SIZE sınırının altında olduğu için kabul edilir.
    }

    # Kodumuz stream=True kullandığı için veriyi requests.get üzerinden parça parça iter_content ile okur.
    # iter_content çağrıldığında dönecek olan sahte parça veri listesini (chunk listesi) tanımlıyoruz.
    fake_response.iter_content = Mock(return_value=[b"bu_sahte_bir_resim_verisi"])

    # requests.get sahte fonksiyonumuz çağrıldığında, yukarıda hazırladığımız fake_response nesnesini dönmesini sağlıyoruz.
    mock_get.return_value = fake_response

    # --- 2. FONKSİYONU ÇAĞIR (Asıl İşlemin Yürütülmesi) ---
    # Test edilmek üzere 1 adet sahte Candidate (resim adayı) oluşturuyoruz.
    candidates = [Candidate(url="http://sahte-site.com/resim.jpg")]

    # download fonksiyonunu bu adayla çalıştırıp dönen sonuçları listeliyoruz.
    results = download(candidates)

    # --- 3. SONUÇLARI DOĞRULA (Assert / Hükümler) ---
    # İndirme başarılı olmalı ve listeye tam olarak 1 adet görsel eklenmiş olmalı.
    assert len(results) == 1, "1 görsel indirilmiş olmalı"

    # İndirilen görselin URL'si, istek attığımız URL ile eşleşmeli.
    assert results[0].url == "http://sahte-site.com/resim.jpg"

    # İndirilen görselin içeriği (data), iter_content'ten dönen veriyle birebir aynı olmalı.
    assert results[0].data == b"bu_sahte_bir_resim_verisi"

    # Content-Type ve extension doğrulaması
    assert results[0].content_type == "image/jpeg"
    assert results[0].extension == ".jpg"

    # Kodumuzun requests.get'i tam olarak hangi parametrelerle (stream=True ve timeout) ve kaç kez çağırdığını kontrol ediyoruz.
    mock_get.assert_called_once_with(
        "http://sahte-site.com/resim.jpg", stream=True, timeout=DOWNLOAD_TIMEOUT
    )


# Bu testte ise HTTP yanıtı dönen kaynağın bir görsel değil, HTML sayfası olması durumunda fonksiyonun bunu reddettiğini doğruluyoruz.
@patch(
    "app.downloader.downloader.config.DOWNLOAD_RETRIES", 2
)  # burda retry sayısını 2 yapıyoruz çünkü range(2+1)
@patch("app.downloader.downloader.requests.get")
def test_download_rejects_html(mock_get):
    # --- 1. SAHTE CEVAP HAZIRLA (HTML Yanıtı Veren Dublör) ---
    fake_response = Mock()
    fake_response.status_code = 200

    # Yanıt başlığında Content-Type'ı text/html yapıyoruz (Görsel olmayan bir sayfa simülasyonu).
    fake_response.headers = {
        "Content-Type": "text/html",  # Görsel olmadığı için downloader.py bunu 'break' ile reddetmeli.
        "Content-Length": "1000",
    }
    mock_get.return_value = fake_response

    # --- 2. FONKSİYONU ÇAĞIR ---
    # HTML sayfası barındıran sahte bir aday oluşturup download fonksiyonunu çağırıyoruz.
    candidates = [Candidate(url="http://sahte-site.com/sayfa.html")]
    results = download(candidates)

    # --- 3. SONUÇLARI DOĞRULA ---
    # Yanıt görsel olmadığı için reddedilmeli ve sonuç listesi boş (0 elemanlı) kalmalıdır.
    assert len(results) == 0, "HTML sayfası reddedilmeli, liste boş olmalı"
    # Tekrar deneme yapılmamalı, tam 1 kez denenip sonlandırılmalıdır.
    assert mock_get.call_count == 1, "HTML reddinde tekrar deneme yapılmamalı"


# Başlıkta (Content-Length) belirtilen boyutun MAX_FILE_SIZE limitini aşması durumunda görselin reddedildiğini test eder.
@patch(
    "app.downloader.downloader.config.DOWNLOAD_RETRIES", 2
)  # burda retry sayısını 2 yapıyoruz çünkü range(2+1)
@patch(
    "app.downloader.downloader.config.MAX_FILE_SIZE", 100
)  # burda max dosya boyutunu 100 byte yapıyoruz
@patch("app.downloader.downloader.requests.get")
def test_download_file_size_exceeded_header(mock_get):
    fake_response = Mock()
    fake_response.status_code = 200
    fake_response.headers = {
        "Content-Type": "image/jpeg",
        "Content-Length": "101",  # 101 byte > limit (100 byte)
    }
    mock_get.return_value = fake_response

    candidates = [Candidate(url="http://sahte-site.com/buyuk-resim.jpg")]
    results = download(candidates)

    assert len(results) == 0, (
        "Dosya boyutu header kontrolünde aşıldığı için indirme iptal edilmeli"
    )
    assert mock_get.call_count == 1, "Header boyut aşımında retry yapılmamalı"


# Veri akışı (iter_content) sırasında indirilen boyutun dinamik olarak limitleri aşması durumunda görselin reddedildiğini test eder.
@patch(
    "app.downloader.downloader.config.DOWNLOAD_RETRIES", 2
)  # burda retry sayısını 2 yapıyoruz çünkü range(2+1)
@patch("app.downloader.downloader.config.MAX_FILE_SIZE", 100)
@patch("app.downloader.downloader.requests.get")
def test_download_file_size_exceeded_dynamic(mock_get):
    fake_response = Mock()
    fake_response.status_code = 200
    fake_response.headers = {
        "Content-Type": "image/jpeg"  # Content-Length yok, dinamik okumaya zorluyoruz
    }
    # İlk parça 50 byte, ikinci parça 60 byte. Toplam 110 byte > limit (100 byte)
    fake_response.iter_content = Mock(return_value=[b"a" * 50, b"b" * 60])
    mock_get.return_value = fake_response

    candidates = [Candidate(url="http://sahte-site.com/dinamik-buyuk-resim.jpg")]
    results = download(candidates)

    assert len(results) == 0, (
        "Dinamik indirme sırasında limit aşıldığı için indirme yarıda kesilmeli"
    )
    assert mock_get.call_count == 1, "Dinamik boyut aşımında retry yapılmamalı"


# Sunucu hatası (5xx veya bağlantı hatası) durumunda downloader'ın retry adeti kadar tekrar deneme yaptığını test eder.
@patch("app.downloader.downloader.config.DOWNLOAD_RETRIES", 2)
@patch("app.downloader.downloader.requests.get")
def test_download_retries_on_server_error(mock_get):
    fake_response = Mock()
    fake_response.status_code = 500
    fake_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "Internal Server Error"
    )
    mock_get.return_value = fake_response

    candidates = [Candidate(url="http://sahte-site.com/hata.jpg")]
    results = download(candidates)

    assert len(results) == 0, "Hata veren site indirilmemeli"
    # DOWNLOAD_RETRIES 2 ise toplamda 3 deneme yapılmalı (1 asıl + 2 retry)
    assert mock_get.call_count == 3


# İstemci hatası (örneğin 404) durumunda tekrar deneme (retry) yapılmaması gerektiğini test eder.
@patch("app.downloader.downloader.config.DOWNLOAD_RETRIES", 2)
@patch("app.downloader.downloader.requests.get")
def test_download_no_retry_on_client_error(mock_get):
    fake_response = Mock()
    fake_response.status_code = 404
    mock_get.return_value = fake_response

    candidates = [Candidate(url="http://sahte-site.com/bulunamadi.jpg")]
    results = download(candidates)

    assert len(results) == 0, "404 veren site indirilmemeli"
    # İstemci hatası olduğu için sadece 1 kez denenmeli, retry yapılmamalıdır
    assert mock_get.call_count == 1


@patch("app.downloader.downloader.config.MAX_CONCURRENT_DOWNLOADS", 2)
@patch("app.downloader.downloader.requests.get")
def test_download_concurrent_execution(mock_get):
    """Eşzamanlı indirme işleminin doğru çalıştığını ve tüm görevlerin tamamlandığını test eder."""
    fake_response = Mock()
    fake_response.status_code = 200
    fake_response.headers = {
        "Content-Type": "image/jpeg",
        "Content-Length": "5000",
    }
    fake_response.iter_content = Mock(return_value=[b"sahte_resim_verisi"])
    mock_get.return_value = fake_response

    # 5 adet aday oluşturalım (MAX_CONCURRENT_DOWNLOADS=2'den büyük olmalı)
    candidates = [
        Candidate(url=f"http://sahte-site.com/resim{i}.jpg") for i in range(5)
    ]

    results = download(candidates)

    # Tüm 5 görsel başarıyla indirilmiş olmalı
    assert len(results) == 5, "Tüm 5 görsel başarıyla indirilmiş olmalı"
    # ThreadPoolExecutor'ın her aday için requests.get'i çağırdığını doğrula
    assert mock_get.call_count == 5


# bu fonksiyonun amacı :
def test_downloaded_image_extension_mapping():
    from app.domain import DownloadedImage

    img_png = DownloadedImage(
        url="u1", data=b"", content_type="image/png; charset=utf-8"
    )
    assert img_png.extension == ".png"

    img_webp = DownloadedImage(url="u2", data=b"", content_type="image/webp")
    assert img_webp.extension == ".webp"

    img_unknown = DownloadedImage(
        url="u3", data=b"", content_type="application/octet-stream"
    )
    assert img_unknown.extension == ".jpg"
