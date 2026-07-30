from pathlib import Path

import pytest

from app import config, pipeline
from app.domain import Candidate, DownloadedImage

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "cat.jpg"


def _fixture_image(candidate: Candidate) -> DownloadedImage:
    return DownloadedImage(
        url=candidate.url,
        data=FIXTURE_PATH.read_bytes(),
        content_type="image/jpeg",
    )


def test_pipeline_run_with_real_yolo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    candidate = Candidate(url="fixture://cat.jpg")

    monkeypatch.setattr(
        pipeline,
        "search",
        lambda _keyword, _fetch_count: [candidate],
    )
    monkeypatch.setattr(
        pipeline,
        "download",
        lambda candidates: [
            _fixture_image(download_candidate) for download_candidate in candidates
        ],
    )
    monkeypatch.setattr(
        config,
        "DOWNLOADS_DIR",
        str(tmp_path),
    )

    result = pipeline.run("kedi", 1)

    assert result.found == 1
    assert len(result.images) == 1
