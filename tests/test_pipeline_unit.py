# tests/test_pipeline_unit.py
import logging
from collections.abc import Callable
from dataclasses import replace
from hashlib import sha256
from unittest.mock import MagicMock

import pytest

from app import config, pipeline, storage
from app.domain import Candidate, DetectionResult, DownloadedImage


def make_candidates(n: int) -> list[Candidate]:
    return [Candidate(url=f"http://example.com/{i}.jpg") for i in range(n)]


def make_download_side_effect() -> Callable[[list[Candidate]], list[DownloadedImage]]:
    def _download(candidates: list[Candidate]) -> list[DownloadedImage]:
        return [
            DownloadedImage(
                url=candidate.url,
                data=f"dummy_image_data_{candidate.url}".encode(),
            )
            for candidate in candidates
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
    fetch_count = int(count * config.OVERFETCH)
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


def test_download_called_once_with_all_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kartın kalbi: adaylar tek tek değil, TOPLU liste olarak download'a gider."""
    count = 5
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)
    confidences = [0.9] * fetch_count

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    pipeline.run("kedi", count)

    assert mock_download.call_count == 1
    mock_download.assert_called_once_with(candidates)
    assert mock_detect.call_count == fetch_count


def test_run_logs_single_summary_line(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Özet log: tek satır, her aramada, keyword + dört sayı (§5 / Karar 5)."""
    count = 2
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)

    passing_count = 3
    confidences = [0.9, 0.6, 0.4] + [0.1] * (fetch_count - passing_count)

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    mock_download = MagicMock(side_effect=make_download_side_effect())
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect(confidences))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    with caplog.at_level(logging.INFO, logger=pipeline.logger.name):
        pipeline.run("kedi", count)

    records = [
        record for record in caplog.records if record.name == pipeline.logger.name
    ]

    assert len(records) == 1
    assert records[0].levelno == logging.INFO

    message = records[0].getMessage()

    assert "kedi" in message
    assert f"istenen={count}" in message
    assert f"aday={fetch_count}" in message
    assert f"inen={fetch_count}" in message
    assert f"tekil={fetch_count}" in message
    assert f"esigi_gecen={passing_count}" in message


def test_partial_result(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 5
    fetch_count = int(count * config.OVERFETCH)
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
    fetch_count = int(count * config.OVERFETCH)
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


def test_duplicate_content_is_detected_and_returned_once(
    monkeypatch: pytest.MonkeyPatch,
    mock_save_image: MagicMock,
) -> None:
    count = 3
    fetch_count = int(count * config.OVERFETCH)
    candidates = make_candidates(fetch_count)

    mock_search = MagicMock(return_value=candidates)
    monkeypatch.setattr(pipeline, "search", mock_search)

    first = DownloadedImage(
        url=candidates[0].url,
        data=b"duplicate image data",
        content_type="image/jpeg",
    )
    unique = DownloadedImage(
        url=candidates[1].url,
        data=b"unique image data",
        content_type="image/jpeg",
    )
    duplicate = DownloadedImage(
        url=candidates[2].url,
        data=first.data,
        content_type="image/png",
    )
    mock_download = MagicMock(return_value=[first, unique, duplicate])
    monkeypatch.setattr(pipeline, "download", mock_download)

    mock_detect = MagicMock(side_effect=make_detect_side_effect([0.9, 0.8]))
    monkeypatch.setattr(pipeline, "detect", mock_detect)

    result = pipeline.run("kedi", count)

    detected_images = [
        detect_call.args[0] for detect_call in mock_detect.call_args_list
    ]
    assert detected_images == [first, unique]
    assert mock_detect.call_count == 2
    assert len(result.images) == 2
    assert result.found == 2
    assert result.found == len(result.images)
    assert [image.url for image in result.images] == [first.url, unique.url]
    assert mock_save_image.call_count == 2


def test_overfetch_call(monkeypatch: pytest.MonkeyPatch) -> None:
    count = 5
    fetch_count = int(count * config.OVERFETCH)
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
    count = config.MAX_COUNT
    fetch_count = int(count * config.OVERFETCH)
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
        pipeline.run("kedi", config.MAX_COUNT + 1)

    mock_search.assert_not_called()
