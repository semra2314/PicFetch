# bu dosyanın amacı internet sitesinden resim indirme işlemini test etmektir. ve bunu yaparken internete ihtiyaç duymaz çünkü internetten gelen verileri sahte verilerle değiştirir. yani mock kullanır. 


import pytest
from unittest.mock import patch, Mock

from app.downloader.downloader import download
from app.domain import Candidate

# @patch dekoratörü, requests.get fonksiyonunu "yakalar" ve yerine sahte bir versiyonunu koyar.
# Bu sahte versiyona "mock_get" adını verdik.
@patch('app.downloader.downloader.requests.get')
def test_download_success(mock_get):
    # 1. SAHTE CEVAP HAZIRLA (Dublörümüz)
    fake_response = Mock()
    fake_response.headers = {
        'Content-Type': 'image/jpeg',
        'Content-Length': '5000'  # 5 KB, sınırın altında
    }
    fake_response.content = b'bu_sahte_bir_resim_verisi' # Bytes verisi
    
    # requests.get çağrıldığında bu sahte cevabı döndürmesini sağla
    mock_get.return_value = fake_response

    # 2. FONKSİYONU ÇAĞIR
    candidates = [Candidate(url="http://sahte-site.com/resim.jpg")]
    results = download(candidates)

    # 3. SONUÇLARI DOĞRULA (Assert)
    assert len(results) == 1, "1 görsel indirilmiş olmalı"
    assert results[0].url == "http://sahte-site.com/resim.jpg"
    assert results[0].data == b'bu_sahte_bir_resim_verisi'
    
    # requests.get'in doğru URL ile tam 1 kez çağrıldığını doğrula
    mock_get.assert_called_once_with("http://sahte-site.com/resim.jpg", timeout=8)


@patch('app.downloader.downloader.requests.get')
def test_download_rejects_html(mock_get):
    # 1. SAHTE CEVAP HAZIRLA (Bu sefer HTML döndüren bir dublör)
    fake_response = Mock()
    fake_response.headers = {
        'Content-Type': 'text/html', # Görsel değil!
        'Content-Length': '1000'
    }
    fake_response.content = b'<html><body>Hata</body></html>'
    mock_get.return_value = fake_response

    # 2. FONKSİYONU ÇAĞIR
    candidates = [Candidate(url="http://sahte-site.com/sayfa.html")]
    results = download(candidates)

    # 3. SONUÇLARI DOĞRULA
    assert len(results) == 0, "HTML sayfası reddedilmeli, liste boş olmalı"