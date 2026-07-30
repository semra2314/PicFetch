from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import config
from app.domain import DownloadedImage, PipelineResult
from app.main import app

client = TestClient(app)


def _mock_result(found: int = 1) -> PipelineResult:
    images: list[DownloadedImage] = []

    for index in range(found):
        content_hash = f"{index:064x}"
        path = Path(config.DOWNLOADS_DIR) / content_hash[:2] / f"{content_hash}.jpg"

        images.append(
            DownloadedImage(
                url=f"https://example.com/{index}.jpg",
                data=f"fake-image-bytes-{index}".encode(),
                content_hash=content_hash,
                path=str(path),
            )
        )

    return PipelineResult(
        images=images,
        requested=found,
        found=found,
    )


def test_empty_keyword_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post(
            "/search",
            json={"keyword": "", "count": 5},
        )

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_whitespace_only_keyword_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post(
            "/search",
            json={"keyword": "   ", "count": 5},
        )

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_missing_keyword_field_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post("/search", json={"count": 5})

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_count_zero_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": 0},
        )

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_count_above_max_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post(
            "/search",
            json={
                "keyword": "kedi",
                "count": config.MAX_COUNT + 1,
            },
        )

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_count_wrong_type_returns_422() -> None:
    with patch("app.pipeline.run") as mock_run:
        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": "abc"},
        )

        assert response.status_code == 422
        mock_run.assert_not_called()


def test_count_at_max_returns_200() -> None:
    with patch("app.pipeline.run") as mock_run:
        mock_run.return_value = _mock_result(found=config.MAX_COUNT)

        response = client.post(
            "/search",
            json={
                "keyword": "kedi",
                "count": config.MAX_COUNT,
            },
        )

        assert response.status_code == 200
        body = response.json()

        assert body["requested"] == config.MAX_COUNT
        assert body["found"] == config.MAX_COUNT


def test_keyword_is_stripped_before_reaching_pipeline() -> None:
    with patch("app.pipeline.run") as mock_run:
        mock_run.return_value = _mock_result()

        response = client.post(
            "/search",
            json={"keyword": "  kedi  ", "count": 5},
        )

        assert response.status_code == 200
        mock_run.assert_called_once_with("kedi", 5)


def test_search_returns_static_image_url() -> None:
    with patch("app.pipeline.run") as mock_run:
        mock_run.return_value = _mock_result()

        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": 1},
        )

        assert response.status_code == 200

        body = response.json()
        content_hash = f"{0:064x}"

        assert body["images"][0]["image_url"] == (
            f"/static/{content_hash[:2]}/{content_hash}.jpg"
        )
        assert body["images"][0]["source_url"] == ("https://example.com/0.jpg")


def test_missing_image_path_returns_500() -> None:
    unsaved_image = DownloadedImage(
        url="https://example.com/cat.jpg",
        data=b"fake-image-bytes",
    )
    result = PipelineResult(
        images=[unsaved_image],
        requested=1,
        found=1,
    )

    with patch("app.pipeline.run", return_value=result):
        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": 1},
        )

    assert response.status_code == 500
    assert "Traceback" not in str(response.json())


def test_pipeline_value_error_returns_400() -> None:
    with patch("app.pipeline.run") as mock_run:
        mock_run.side_effect = ValueError("count en fazla 50 olabilir")

        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": 5},
        )

        assert response.status_code == 400


def test_pipeline_unexpected_exception_returns_500_without_traceback() -> None:
    with patch("app.pipeline.run") as mock_run:
        mock_run.side_effect = RuntimeError("beklenmedik çökme")

        response = client.post(
            "/search",
            json={"keyword": "kedi", "count": 5},
        )

        assert response.status_code == 500
        body = response.json()

        assert "beklenmedik çökme" not in str(body)
        assert "Traceback" not in str(body)
