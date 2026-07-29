"""search fonksiyonunun 5 koşulda çalışıp çalışmadığı test edilmesi"""

from app.search.search import search
from app.domain import Candidate
from unittest.mock import patch, call  # swap testi call kullanıyor
from app import config
import logging

# normal durum
# sonucun 0 (boş) olması durumu
# hata oluşma (error) durumu
# recovery
# eksik anahtar


def test_search_normal():

    with patch("app.search.search.DDGS") as mock_ddgs:
        # gerçek DDGS servisini mock ile değiştirerek
        # dış bağımlılığı kaldırıyoruz

        mock_ddgs.return_value.images.return_value = [
            {"image": "http://ornek.com/1.jpg"},
            {"image": "http://ornek.com/2.jpg"},
            {"image": "http://ornek.com/3.jpg"},
        ]
        result = search("cat", 3)  # Test edilen search() fonksiyonunu çağırıyoruz
        assert len(result) == 3
        assert isinstance(
            result[0], Candidate
        )  # İlk elemanın Candidate nesnesi olduğunu doğruluyoruz
        assert (
            result[0].url == "http://ornek.com/1.jpg"
        )  # İlk Candidate nesnesinin URL bilgisinin doğru olduğunu kontrol ediyoruz


def test_search_empty(caplog):
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_ddgs.return_value.images.return_value = []
        with caplog.at_level(logging.WARNING):
            result = search("cat", 3)
        assert result == []  # dönen değer  boş liste mi diye kontrol eder
        assert "0 sonuç" in caplog.text


def test_search_error(caplog):
    with patch("app.search.search.DDGS") as mock_ddgs:
        with patch("app.search.search.time.sleep"):
            mock_ddgs.return_value.images.side_effect = Exception("ağ hatası")
            with caplog.at_level(logging.ERROR):
                result = search("cat", 3)
            assert result == []
            assert mock_ddgs.return_value.images.call_count == config.SEARCH_RETRIES
            assert "failed" in caplog.text


def test_search_recovers():
    with patch("app.search.search.DDGS") as mock_ddgs:
        with patch("app.search.search.time.sleep"):
            mock_ddgs.return_value.images.side_effect = [
                Exception("ağ hatası"),  # 1. deneme patlar
                [{"image": "http://ornek.com/1.jpg"}],  # 2. deneme başarılı
            ]
            result = search("cat", 3)
            assert len(result) == 1
            assert result[0].url == "http://ornek.com/1.jpg"
            assert (
                mock_ddgs.return_value.images.call_count == 2
            )  # call_count 2 kez denendi mi (1 patlama + 1 başarı)


def test_search_skips_missing_key(caplog):  # eksik anahtar atlanmalı durumu
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_ddgs.return_value.images.return_value = [
            {"image": "http://ornek.com/1.jpg"},
            {},  # eksik anahtar atlandı
            {"image": "http://ornek.com/2.jpg"},
        ]
        with caplog.at_level(logging.WARNING):
            result = search("cat", 3)
        assert len(result) == 2
        assert "atlandı" in caplog.text


def test_search_swaps_when_min_greater_than_max(monkeypatch) -> None:
    monkeypatch.setattr(config, "SEARCH_RETRY_DELAY_MIN", 5)
    monkeypatch.setattr(config, "SEARCH_RETRY_DELAY_MAX", 2)
    with (
        patch("app.search.search.DDGS") as mock_ddgs,
        patch("app.search.search.time.sleep"),
        patch("app.search.search.random.randint") as mock_randint,
    ):
        mock_ddgs.return_value.images.side_effect = Exception("DDGS error")
        result = search("araba", 3)
        assert mock_randint.call_args_list == [call(2, 5)] * config.SEARCH_RETRIES
        assert result == []
