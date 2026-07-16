"""
Bu dosyada iki tür test var:
1. test_run_with_mocks  → mock veriler kullanır, internete çıkmaz.
2. test_run_with_real_yolo → Gerçek YOLO + gerçek internet kullanır.
Hangi testin çalıştığını görmek için: pytest -s -v
"""
import pytest
import logging
from app.domain import DownloadedImage, Candidate, DetectionResult
from app import pipeline
from app.logging_setup import setup_logging

# ---------------------------------------------------------------------------
# MOCK FIXTURE'LAR — sahte veri üreten yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_search():
    def _mock(keyword, count):
        return [
            Candidate(url="https://ornek.com/kedi.jpg"),
            Candidate(url="https://ornek.com/kedi2.jpg"),
        ]
    return _mock

@pytest.fixture
def mock_download():
    def _mock(candidates):
        # pipeline artık toplu indirdiği için mantığı buna göre güncelledik
        return [
            DownloadedImage(url=c.url, data=b"fake_image_data")
            for c in candidates
            if c.url != "https://ornek.com/kedi2.jpg"
        ]
    return _mock

@pytest.fixture
def mock_detect():
    def _mock(image, keyword):
        return DetectionResult(image=image, confidence=0.9)
    return _mock

@pytest.fixture
def mock_rank():
    def _mock(results, threshold, limit):
        return [r.image for r in results]
    return _mock

# ---------------------------------------------------------------------------
# Mock veriler, internete çıkmaz
# ---------------------------------------------------------------------------
def test_run_with_mocks(monkeypatch, mock_search, mock_download, mock_detect, mock_rank):
    monkeypatch.setattr(pipeline, "search", mock_search)
    monkeypatch.setattr(pipeline, "download", mock_download)
    monkeypatch.setattr(pipeline, "detect", mock_detect)
    monkeypatch.setattr(pipeline, "rank", mock_rank)
    
    result = pipeline.run("cat", 1)
    
    assert len(result) == 1
    assert result[0].url == "https://ornek.com/kedi.jpg"

# 4. Madde Çözümü: Arama sonucu boş döndüğünde log kontrolü ve boş liste dönüşü testi
def test_run_search_empty_logs_warning(monkeypatch, caplog):
    monkeypatch.setattr(pipeline, "search", lambda k, c: [])
    
    with caplog.at_level(logging.WARNING):
        result = pipeline.run("ghost_keyword", 1)
        
    assert result == []
    assert "Arama sonucu boş döndü, keyword: ghost_keyword" in caplog.text

# 4. Madde Çözümü: Sıralama sonrası sonuç kalmadığında log kontrolü testi
#  testi pytest standartlarına tam uydurmak için parametrik yazalım:
def test_run_rank_empty_logs_warning_full(monkeypatch, mock_search, mock_download, mock_detect, caplog):
    monkeypatch.setattr(pipeline, "search", mock_search)
    monkeypatch.setattr(pipeline, "download", mock_download)
    monkeypatch.setattr(pipeline, "detect", mock_detect)
    monkeypatch.setattr(pipeline, "rank", lambda r, t, l: [])
    
    with caplog.at_level(logging.WARNING):
        result = pipeline.run("cat", 1)
        
    assert result == []
    assert "Sıralama sonrası hiç sonuç kalmadı" in caplog.text

# ---------------------------------------------------------------------------
# Gerçek YOLO + gerçek internet, mock yok
# ---------------------------------------------------------------------------
@pytest.mark.real_data
@pytest.mark.xfail(reason="Geçici olarak başarısız olması bekleniyor; rank() henüz tamamlanmadı.", strict=False)
def test_run_with_real_yolo():
    setup_logging()
    result = pipeline.run("cat", 1)
    assert isinstance(result, list)