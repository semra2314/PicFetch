# tests/test_pipeline_unit.py
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from app import pipeline, storage
from app.config import MAX_COUNT, OVERFETCH
from app.domain import Candidate, DetectionResult, DownloadedImage


def make_candidates(n: int) -> list[Candidate]:
    return [Candidate(url=f"http://example.com/{i}.jpg") for i in range(n)]


def make_download_side_effect() -> Callable[[list[Candidate]], list[DownloadedImage]]:
    def _download(candidates: list[Candidate]) -> list[DownloadedImage]:
        candidate = candidates[0]

        return [
            DownloadedImage(
                url=candidate.url,
                data=f"dummy_image_data_{candidate.url}".encode(),
            )
        ]

    return _download


def make_detect_side_effect(
    confidences: list[float],
) -> Callable[[DownloadedImage, str], DetectionResult]:
    confidence_iterator = iter(confidences)

    def _detect(
        image: DownloadedImage,
        _keyword: str,
    ) -> DetectionResult:
        return DetectionResult(
            image=image,
            confidence=next(confidence_iterator),
        )

    return _detect


@pytest.fixture(autouse=True)
def mock_save_image(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_save = MagicMock()

    def _save_image(image: DownloadedImage) -> DownloadedImage:
        content_hash = sha256(image.data).hexdigest()
        path = f"data/downloads/{content_hash[:2]}/{content_hash}{image.extension}"

        return replace(
            image,
            content_hash=content_hash,
            path=path,
        )

    mock_save.side_effect = _save_image
    monkeypatch.setattr(storage, "save_image", mock_save)

    return mock_save


def test_full_result(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 5
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert len(result.images) == count
    assert result.found == count
    assert result.found == len(result.images)
    assert all(image.path is not None for image in result.images)
    assert all(image.content_hash is not None for image in result.images)

    mock_search.assert_called_once_with("kedi", fetch_count)
    assert mock_save_image.call_count == count


def test_partial_result(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 5
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)

    passing_count = 2
    confidences = [0.6, 0.9] + [0.1] * (fetch_count - passing_count)

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert len(result.images) == passing_count
    assert result.found == len(result.images)
    assert mock_save_image.call_count == passing_count

    saved_urls = [save_call.args[0].url for save_call in mock_save_image.call_args_list]

    # İkinci adayın skoru daha yüksek olduğu için önce kaydedilmelidir.
    assert saved_urls == [
        candidates[1].url,
        candidates[0].url,
    ]


def test_empty_result(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 5
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.1] * fetch_count

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert result.images == []
    assert result.found == 0
    assert result.found == len(result.images)
    mock_save_image.assert_not_called()


def test_duplicate_hashes_remain_in_results(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 2
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9, 0.8] + [0.1] * (fetch_count - 2)

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    duplicate_hash = "a" * 64
    duplicate_path = f"data/downloads/aa/{duplicate_hash}.jpg"

    def _save_with_duplicate_hash(
        image: DownloadedImage,
    ) -> DownloadedImage:
        return replace(
            image,
            content_hash=duplicate_hash,
            path=duplicate_path,
        )

    mock_save_image.side_effect = _save_with_duplicate_hash

    result = pipeline.run("kedi", count)

    assert len(result.images) == 2
    assert result.found == 2
    assert all(image.content_hash == duplicate_hash for image in result.images)
    assert mock_save_image.call_count == 2


def test_overfetch_call(monkeypatch: pytest.MonkeyPatch) -> None:
    count = 5
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    pipeline.run("kedi", count)

    mock_search.assert_called_once_with("kedi", fetch_count)


def test_invalid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", 0)

    mock_search.assert_not_called()


def test_count_at_max_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    count = MAX_COUNT
    fetch_count = int(count * OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    assert result.found == count


def test_count_above_max_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_search = MagicMock()
    monkeypatch.setattr(pipeline, "search", mock_search)

    with pytest.raises(ValueError):
        pipeline.run("kedi", MAX_COUNT + 1)

    mock_search.assert_not_called()
