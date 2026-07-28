import hashlib
from pathlib import Path
import pytest
from app import config, storage
from app.domain import DownloadedImage


def test_save_image_populates_path_and_content_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_data = b"dummy image data"
    downloads_path = tmp_path / "downloads"

    monkeypatch.setattr(
        config,
        "DOWNLOADS_DIR",
        str(downloads_path),
    )

    image = DownloadedImage(
        url="https://ornek1.com/image",
        data=image_data,
        content_type="image/png",
    )

    saved_image = storage.save_image(image)
    expected_hash = hashlib.sha256(image_data).hexdigest()

    assert saved_image.content_hash == expected_hash
    assert saved_image.path is not None

    saved_path = Path(saved_image.path)

    assert saved_path.is_file()
    assert saved_path.read_bytes() == image_data
    assert saved_path.parent == downloads_path / expected_hash[:2]


def test_save_image_writes_same_bytes_only_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image_data = b"dummy image data"
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))

    image = DownloadedImage(
        url="https://ornek1.com/image", data=image_data, content_type="image/png"
    )

    first_result = storage.save_image(image)
    second_result = storage.save_image(image)

    saved_files = [path for path in downloads_path.rglob("*") if path.is_file()]

    assert len(saved_files) == 1
    assert first_result.path == second_result.path


@pytest.mark.parametrize(
    ("content_type", "expected_suffix"),
    [
        ("image/jpeg", ".jpg"),
        ("image/png", ".png"),
        ("image/webp", ".webp"),
        ("image/jpeg; charset=utf-8", ".jpg"),
    ],
)
def test_save_image_uses_extension_from_content_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
    expected_suffix: str,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))

    image = DownloadedImage(
        url="https://ornek1.com/image",
        data=b"extension test data",
        content_type=content_type,
    )

    saved_image = storage.save_image(image)

    assert saved_image.path is not None
    assert Path(saved_image.path).suffix == expected_suffix


def test_save_image_keeps_one_file_for_same_bytes_with_different_content_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))

    image_data = b"same bytes from different servers"

    jpeg_image = DownloadedImage(
        url="https://birinci-sunucu.com/image",
        data=image_data,
        content_type="image/jpeg",
    )
    png_image = DownloadedImage(
        url="https://ikinci-sunucu.com/image",
        data=image_data,
        content_type="image/png",
    )

    first_result = storage.save_image(jpeg_image)
    second_result = storage.save_image(png_image)

    saved_files = [path for path in downloads_path.rglob("*") if path.is_file()]

    assert len(saved_files) == 1
    assert first_result.content_hash == second_result.content_hash
    assert first_result.path == second_result.path
    assert saved_files[0].suffix == ".jpg"


def test_save_image_does_not_mutate_input_image(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))

    original_image = DownloadedImage(
        url="https://ornek1.com/image",
        data=b"immutable image data",
        content_type="image/png",
    )

    saved_image = storage.save_image(original_image)

    assert saved_image is not original_image

    assert original_image.content_hash is None
    assert original_image.path is None

    assert saved_image.content_hash is not None
    assert saved_image.path is not None
