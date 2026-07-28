# tests/test_pipeline_unit.py
from unittest.mock import MagicMock

import pytest

from app import pipeline
from app import config
from app.domain import Candidate, DetectionResult, DownloadedImage


# Ağ isteği yapmadan sahte arama sonuçları oluşturur.
def make_candidates(n: int) -> list[Candidate]:
    return [Candidate(url=f"http://example.com/{i}.jpg") for i in range(n)]


def make_download_side_effect():
    def _download(candidates):
        # detect de mock'landığı için gerçek görsel verisine ihtiyaç yoktur.
        return [
            DownloadedImage(url=candidate.url, data=b"dummy_image_data")
            for candidate in candidates
        ]

    return _download


def make_detect_side_effect(confidences: list[float]):
    # Her detect çağrısında sıradaki confidence değerini kullanır.
    confidence_iterator = iter(confidences)

    def _detect(image, keyword):
        return DetectionResult(
            image=image,
            confidence=next(confidence_iterator),
        )

    return _detect


def test_full_result(monkeypatch):
    count = 5
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock()
    mock_search.return_value = candidates

    # Pipeline fonksiyonları kendi namespace'ine import ettiği için buradan patch'lenir.
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock()
    mock_download.side_effect = make_download_side_effect()
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock()
    mock_detect.side_effect = make_detect_side_effect(confidences)
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    # Rank mock'lanmaz; gerçek eşik, sıralama ve limit mantığı çalışır.
    result = pipeline.run("kedi", count)

    assert result.images is not None
    assert len(result.images) == count
    assert result.found == count
    assert mock_search.call_args[0][1] == fetch_count
    assert result.found == len(result.images)

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)


def test_partial_result(monkeypatch):
    count = 5
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)

    # Yalnızca iki adayın detection eşiğini geçmesini sağlarız.
    passing_count = 2
    confidences = [0.9] * passing_count + [0.1] * (fetch_count - passing_count)

    mock_search = MagicMock()
    mock_search.return_value = candidates
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock()
    mock_download.side_effect = make_download_side_effect()
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock()
    mock_detect.side_effect = make_detect_side_effect(confidences)
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert len(result.images) == passing_count
    assert result.found == len(result.images)

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)


def test_empty_result(monkeypatch):
    count = 5
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)

    # Tüm confidence değerleri eşik altında kalır.
    confidences = [0.1] * fetch_count

    mock_search = MagicMock()
    mock_search.return_value = candidates
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock()
    mock_download.side_effect = make_download_side_effect()
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock()
    mock_detect.side_effect = make_detect_side_effect(confidences)
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert result.images == []
    assert result.found == 0
    assert result.found == len(result.images)

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)


def test_overfetch_call(monkeypatch):
    count = 5
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock()
    mock_search.return_value = candidates
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock()
    mock_download.side_effect = make_download_side_effect()
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock()
    mock_detect.side_effect = make_detect_side_effect(confidences)
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    pipeline.run("kedi", count)

    # Search, kullanıcı sayısıyla değil overfetch uygulanmış sayıyla çağrılmalıdır.
    mock_search.assert_called_once_with("kedi", fetch_count)

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)


def test_invalid_input(monkeypatch):
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", 0)

    # Geçersiz girdi, dış işlem başlamadan reddedilmelidir.
    mock_search.assert_not_called()


def test_count_at_max_is_accepted(monkeypatch):
    # Test için kabul edilebilir maksimum istek sayısını belirliyoruz
    count = config.MAX_COUNT
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock()
    mock_search.return_value = candidates
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock()
    mock_download.side_effect = make_download_side_effect()
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock()
    mock_detect.side_effect = make_detect_side_effect(confidences)
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert result.found == count

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)


def test_count_above_max_is_rejected(monkeypatch):
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", config.MAX_COUNT + 1)

    # İstek limit aşımı nedeniyle reddedildiği için
    # arama fonksiyonunun HİÇ çağrılmadığını doğruluyoruz
    mock_search.assert_not_called()
