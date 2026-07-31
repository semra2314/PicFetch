import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app import config
from app.domain import DownloadedImage
from app.storage import storage


def _image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    with Image.new("RGB", (2, 2), color="red") as image:
        image.save(buffer, format=image_format)
    return buffer.getvalue()


def _ico_bytes() -> bytes:
    buffer = BytesIO()
    with Image.new("RGBA", (32, 32), color=(255, 0, 0, 255)) as image:
        image.save(buffer, format="ICO")
    return buffer.getvalue()


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


def test_save_image_prefers_extension_from_image_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))
    image = DownloadedImage(
        url="https://ornek1.com/image",
        data=_image_bytes("PNG"),
        content_type="image/jpeg",
    )

    saved_image = storage.save_image(image)

    assert saved_image.path is not None
    assert Path(saved_image.path).suffix == ".png"


def test_save_image_uses_content_type_fallback_when_load_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))
    buffer = BytesIO()
    with Image.new("RGB", (64, 64), color="red") as image:
        image.save(buffer, format="PNG")
    truncated_png = buffer.getvalue()[:100]

    with Image.open(BytesIO(truncated_png)) as recognized_image:
        assert recognized_image.format == "PNG"
        with pytest.raises(OSError):
            recognized_image.load()

    image = DownloadedImage(
        url="https://ornek1.com/image",
        data=truncated_png,
        content_type="image/jpeg",
    )

    saved_image = storage.save_image(image)

    assert saved_image.path is not None
    saved_path = Path(saved_image.path)
    assert saved_path.suffix == ".jpg"
    assert saved_path.read_bytes() == truncated_png


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


def test_save_image_concurrently_writes_one_complete_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))
    image_data = _image_bytes("PNG")
    images = [
        DownloadedImage(
            url="https://birinci-sunucu.com/image",
            data=image_data,
            content_type="image/jpeg",
        ),
        DownloadedImage(
            url="https://ikinci-sunucu.com/image",
            data=image_data,
            content_type="image/webp",
        ),
    ]
    real_replace = os.replace
    replace_barrier = threading.Barrier(2)
    replace_calls: list[tuple[Path, Path]] = []
    calls_lock = threading.Lock()

    def synchronized_replace(
        source: os.PathLike[str], destination: os.PathLike[str]
    ) -> None:
        with calls_lock:
            replace_calls.append((Path(source), Path(destination)))
        replace_barrier.wait(timeout=5)
        real_replace(source, destination)

    monkeypatch.setattr(storage.os, "replace", synchronized_replace)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(storage.save_image, image) for image in images]
        saved_images = [future.result(timeout=10) for future in futures]

    saved_files = [path for path in downloads_path.rglob("*") if path.is_file()]
    expected_directory = downloads_path / hashlib.sha256(image_data).hexdigest()[:2]

    assert len(replace_calls) == 2
    assert len({source for source, _ in replace_calls}) == 2
    assert all(source.parent == expected_directory for source, _ in replace_calls)
    assert len({destination for _, destination in replace_calls}) == 1
    assert saved_images[0].path == saved_images[1].path
    assert len(saved_files) == 1
    assert saved_files[0].suffix == ".png"
    assert saved_files[0].read_bytes() == image_data
    assert list(downloads_path.rglob("*.tmp")) == []


def test_save_image_concurrently_uses_byte_derived_extension_for_ico(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))
    image_data = _ico_bytes()
    with Image.open(BytesIO(image_data)) as detected_image:
        detected_image.load()
        assert detected_image.format == "ICO"
    images = [
        DownloadedImage(
            url="https://birinci-sunucu.com/image",
            data=image_data,
            content_type="image/jpeg",
        ),
        DownloadedImage(
            url="https://ikinci-sunucu.com/image",
            data=image_data,
            content_type="image/png",
        ),
    ]
    real_replace = os.replace
    replace_barrier = threading.Barrier(2)
    replace_calls: list[tuple[Path, Path]] = []
    calls_lock = threading.Lock()

    def synchronized_replace(
        source: os.PathLike[str], destination: os.PathLike[str]
    ) -> None:
        with calls_lock:
            replace_calls.append((Path(source), Path(destination)))
        replace_barrier.wait(timeout=5)
        real_replace(source, destination)

    monkeypatch.setattr(storage.os, "replace", synchronized_replace)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(storage.save_image, image) for image in images]
        saved_images = [future.result(timeout=10) for future in futures]

    saved_files = [path for path in downloads_path.rglob("*") if path.is_file()]
    content_hash = hashlib.sha256(image_data).hexdigest()
    expected_path = downloads_path / content_hash[:2] / f"{content_hash}.ico"

    assert len(replace_calls) == 2
    assert len({source for source, _ in replace_calls}) == 2
    assert {destination for _, destination in replace_calls} == {expected_path}
    assert saved_images[0].path == saved_images[1].path
    assert saved_images[0].path == str(expected_path)
    assert len(saved_files) == 1
    assert saved_files[0] == expected_path
    assert saved_files[0].read_bytes() == image_data
    assert list(downloads_path.rglob("*.tmp")) == []


def test_save_image_cleans_up_temporary_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    downloads_path = tmp_path / "downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(downloads_path))
    image = DownloadedImage(
        url="https://ornek1.com/image",
        data=_image_bytes("PNG"),
        content_type="image/png",
    )

    def fail_replace(source: os.PathLike[str], destination: os.PathLike[str]) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(storage.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        storage.save_image(image)

    assert [path for path in downloads_path.rglob("*") if path.is_file()] == []


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
