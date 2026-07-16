"""
Bu dosyada iki tür test var:
1. test_run_with_mocks  → HIZLI test, mock veriler kullanır, internete çıkmaz.
2. test_run_with_real_yolo → YAVAŞ test, gerçek YOLO + gerçek internet kullanır.
Hangi testin çalıştığını görmek için: pytest -s -v
"""
import pytest
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
# HIZLI TEST — mock veriler, internete çıkmaz
# ---------------------------------------------------------------------------

def test_run_with_mocks(monkeypatch, mock_search, mock_download, mock_detect, mock_rank):
    monkeypatch.setattr(pipeline, "search", mock_search)
    monkeypatch.setattr(pipeline, "download", mock_download)
    monkeypatch.setattr(pipeline, "detect", mock_detect)
    monkeypatch.setattr(pipeline, "rank", mock_rank)

    result = pipeline.run("cat", 1)

    print("\n=== MOCK TEST SONUCU ===")
    print("Sonuç:", result)
    print("========================\n")

    assert len(result) == 1
    assert result[0].url == "https://ornek.com/kedi.jpg"


# ---------------------------------------------------------------------------
# YAVAŞ TEST — gerçek YOLO + gerçek internet, mock yok
# ---------------------------------------------------------------------------
    print("\n=== GERÇEK TEST SONUCU (YOLO + internet) ===")
    print("Sonuç:", result)
    print("=============================================\n")
    
@pytest.mark.slow
@pytest.mark.xfail(reason="rank() henüz implement edilmedi, şu an None dönüyor", strict=False)
def test_run_with_real_yolo():
    setup_logging()
    result = pipeline.run("cat", 1)
    assert isinstance(result, list)