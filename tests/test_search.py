"""search fonksiyonunun 3 koşulda çalışıp çalışmadığı test edilmesi"""

from app.search.search import search
from app.domain import Candidate
from unittest.mock import patch
import logging

# normal durum
# sonucun 0 (boş) olması durumu
# hata oluşma (error) durumu


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
            assert mock_ddgs.return_value.images.call_count == 3
            assert "failed" in caplog.text
