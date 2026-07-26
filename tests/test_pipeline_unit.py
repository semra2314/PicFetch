# tests/test_pipeline_unit.py
from unittest.mock import MagicMock

import pytest

from app import pipeline
from app.config import OVERFETCH
from app.domain import Candidate, DetectionResult, DownloadedImage


def make_candidates(n: int) -> list[Candidate]:
    return [Candidate(url=f"http://example.com/{i}.jpg") for i in range(n)]


def make_download_side_effect():
    def _download(candidates):
        candidate = candidates[0]
        return [DownloadedImage(url=candidate.url, data=b"dummy_image_data")]

    return _download


def make_detect_side_effect(confidences: list[float]):
    it = iter(confidences)

    def _detect(image, keyword):
        return DetectionResult(image=image, confidence=next(it))

    return _detect


def test_full_result(monkeypatch):
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

    passing_count = 2  # kaç tanesinin eşiği geçmesini istiyorsun, sen seç
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


def test_empty_result(monkeypatch):
    count = 5
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)

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

    pipeline.run("kedi", count)

    mock_search.assert_called_once_with("kedi", fetch_count)


def test_invalid_input(monkeypatch):
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", 0)

    mock_search.assert_not_called()
