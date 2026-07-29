# tests/test_pipeline_unit.py
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from app import pipeline, storage
from app.config import MAX_COUNT, OVERFETCH
from app.domain import Candidate, DetectionResult, DownloadedImage


# Ağ isteği yapmadan sahte arama sonuçları oluşturur.
def make_candidates(n: int) -> list[Candidate]:
    return [Candidate(url=f"http://example.com/{i}.jpg") for i in range(n)]


def make_download_side_effect():
    def _download(candidates):
        candidate = candidates[0]

        # detect de mock'landığı için gerçek görsel verisine ihtiyaç yoktur.
        return [DownloadedImage(url=candidate.url, data=b"dummy_image_data")]

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


def make_save_image_side_effect():
    # Gerçek diske yazmadan, path ve content_hash sahte doldurulur.
    def _save_image(image):
        fake_hash = f"hash_{image.url}"
        return replace(
            image,
            content_hash=fake_hash,
            path=f"data/downloads/fake/{fake_hash}{image.extension}",
        )

    return _save_image


def test_full_result(monkeypatch):
    count = 5
    fetch_count = int(count * OVERFETCH)
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

    mock_save_image = MagicMock()
    mock_save_image.side_effect = make_save_image_side_effect()
    monkeypatch.setattr(storage, "save_image", mock_save_image)

    # Rank mock'lanmaz; gerçek eşik, sıralama ve limit mantığı çalışır.
    result = pipeline.run("kedi", count)

    assert result.images is not None
    assert len(result.images) == count
    assert result.found == count
    assert mock_search.call_args[0][1] == fetch_count
    assert result.found == len(result.images)


def test_partial_result(monkeypatch):
    count = 5
    fetch_count = int(count * OVERFETCH)
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

    mock_save_image = MagicMock()
    mock_save_image.side_effect = make_save_image_side_effect()
    monkeypatch.setattr(storage, "save_image", mock_save_image)

    result = pipeline.run("kedi", count)

    assert len(result.images) == passing_count
    assert result.found == len(result.images)


def test_empty_result(monkeypatch):
    count = 5
    fetch_count = int(count * OVERFETCH)
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

    # NOT: ranked boş döndüğü için save_image hiç çağrılmaz; mock'lamaya gerek yok.
    result = pipeline.run("kedi", count)

    assert result.images == []
    assert result.found == 0
    assert result.found == len(result.images)


def test_overfetch_call(monkeypatch):
    count = 5
    fetch_count = int(count * OVERFETCH)
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

    mock_save_image = MagicMock()
    mock_save_image.side_effect = make_save_image_side_effect()
    monkeypatch.setattr(storage, "save_image", mock_save_image)

    pipeline.run("kedi", count)

    # Search, kullanıcı sayısıyla değil overfetch uygulanmış sayıyla çağrılmalıdır.
    mock_search.assert_called_once_with("kedi", fetch_count)


def test_invalid_input(monkeypatch):
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", 0)

    # Geçersiz girdi, dış işlem başlamadan reddedilmelidir.
    mock_search.assert_not_called()


def test_count_at_max_is_accepted(monkeypatch):
    # Test için kabul edilebilir maksimum istek sayısını belirliyoruz
    count = MAX_COUNT
    fetch_count = int(count * OVERFETCH)
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

    mock_save_image = MagicMock()
    mock_save_image.side_effect = make_save_image_side_effect()
    monkeypatch.setattr(storage, "save_image", mock_save_image)

    result = pipeline.run("kedi", count)

    assert result.found == count


def test_count_above_max_is_rejected(monkeypatch):
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", MAX_COUNT + 1)

    # İstek limit aşımı nedeniyle reddedildiği için
    # arama fonksiyonunun HİÇ çağrılmadığını doğruluyoruz
    mock_search.assert_not_called()