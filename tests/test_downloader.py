# bu dosyanın amacı internet sitesinden resim indirme işlemini test etmektir. ve bunu yaparken internete ihtiyaç duymaz çünkü internetten gelen verileri sahte verilerle değiştirir. yani mock kullanır. 

import pytest
# unittest.mock kütüphanesinden patch (fonksiyonu taklit etmek için) ve Mock (sahte nesne üretmek için) modüllerini içe aktarıyoruz.
from unittest.mock import patch, Mock

# Test edeceğimiz download fonksiyonunu ve test girdisi olarak kullanacağımız Candidate sınıfını projeden çağırıyoruz.
from app.downloader.downloader import download
from app.domain import Candidate

# @patch dekoratörü, requests.get fonksiyonunu geçici olarak yakalar ve yerine sahte (dublör) bir fonksiyon koyar.
# Bu sahte versiyona test fonksiyonunun argümanı olan "mock_get" adını verdik.
@patch('app.downloader.downloader.requests.get')
def test_download_success(mock_get):
    # --- 1. SAHTE CEVAP HAZIRLA (Mock/Dublör Yapılandırılması) ---
    # İstek başarılı olduğunda dönecek olan HTTP yanıtını simüle etmek için sahte bir Mock nesnesi oluşturuyoruz.
    fake_response = Mock()
    
    # Sunucunun başarılı döndüğünü belirtmek için HTTP Status Code'u 200 yapıyoruz.
    fake_response.status_code = 200
    
    # HTTP Başlıklarını (Headers) simüle ediyoruz. Görsel türünü ve boyutunu belirtiyoruz.
    fake_response.headers = {
        'Content-Type': 'image/jpeg',  # downloader.py içerisindeki "image/" kontrolünden geçebilmesi için.
        'Content-Length': '5000'       # 5 KB dosya boyutu, config.MAX_FILE_SIZE sınırının altında olduğu için kabul edilir.
    }
    
    # Kodumuz stream=True kullandığı için veriyi requests.get üzerinden parça parça iter_content ile okur.
    # iter_content çağrıldığında dönecek olan sahte parça veri listesini (chunk listesi) tanımlıyoruz.
    fake_response.iter_content = Mock(return_value=[b'bu_sahte_bir_resim_verisi'])
    
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
    assert results[0].data == b'bu_sahte_bir_resim_verisi'
    
    # Kodumuzun requests.get'i tam olarak hangi parametrelerle (stream=True ve timeout) ve kaç kez çağırdığını kontrol ediyoruz.
    mock_get.assert_called_once_with("http://sahte-site.com/resim.jpg", stream=True, timeout=8)


# Bu testte ise HTTP yanıtı dönen kaynağın bir görsel değil, HTML sayfası olması durumunda fonksiyonun bunu reddettiğini doğruluyoruz.
@patch('app.downloader.downloader.requests.get')
def test_download_rejects_html(mock_get):
    # --- 1. SAHTE CEVAP HAZIRLA (HTML Yanıtı Veren Dublör) ---
    fake_response = Mock()
    fake_response.status_code = 200
    
    # Yanıt başlığında Content-Type'ı text/html yapıyoruz (Görsel olmayan bir sayfa simülasyonu).
    fake_response.headers = {
        'Content-Type': 'text/html',  # Görsel olmadığı için downloader.py bunu 'break' ile reddetmeli.
        'Content-Length': '1000'
    }
    mock_get.return_value = fake_response

    # --- 2. FONKSİYONU ÇAĞIR ---
    # HTML sayfası barındıran sahte bir aday oluşturup download fonksiyonunu çağırıyoruz.
    candidates = [Candidate(url="http://sahte-site.com/sayfa.html")]
    results = download(candidates)

    # --- 3. SONUÇLARI DOĞRULA ---
    # Yanıt görsel olmadığı için reddedilmeli ve sonuç listesi boş (0 elemanlı) kalmalıdır.
    assert len(results) == 0, "HTML sayfası reddedilmeli, liste boş olmalı"

