import hashlib
import os
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image, UnidentifiedImageError

from app import config
from app.domain import DownloadedImage

_IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
    "BMP": ".bmp",
    "TIFF": ".tiff",
}


def _extension_from_image_format(image_format: str) -> str:
    normalized_format = image_format.upper()
    canonical_extension = _IMAGE_FORMAT_EXTENSIONS.get(normalized_format)
    if canonical_extension is not None:
        return canonical_extension

    registered_extensions = sorted(
        extension.lower()
        for extension, registered_format in Image.registered_extensions().items()
        if registered_format.upper() == normalized_format
        and extension.startswith(".")
        and extension[1:].isascii()
        and extension[1:].isalnum()
    )
    if registered_extensions:
        return registered_extensions[0]

    safe_format_name = "".join(
        character.lower()
        for character in normalized_format
        if character.isascii() and character.isalnum()
    )
    return f".{safe_format_name}" if safe_format_name else ".img"


def _extension_from_image_data(image: DownloadedImage) -> str:
    try:
        with Image.open(BytesIO(image.data)) as detected_image:
            detected_image.load()
            image_format = detected_image.format
    except (UnidentifiedImageError, OSError):
        return image.extension

    if image_format is None:
        return ".img"
    return _extension_from_image_format(image_format)


def _write_atomically(path: Path, data: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(data)

        try:
            os.replace(temporary_path, path)
        except OSError:
            # Windows aynı hedefe eşzamanlı replace çağrılarından birini
            # reddedebilir. Diğer writer aynı, eksiksiz içeriği yazdıysa işlem
            # zaten başarıyla tamamlanmıştır; diğer tüm hataları koru.
            try:
                target_matches = path.read_bytes() == data
            except OSError:
                target_matches = False
            if not target_matches:
                raise
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def save_image(image: DownloadedImage) -> DownloadedImage:
    content_hash = hashlib.sha256(image.data).hexdigest()
    directory = Path(config.DOWNLOADS_DIR) / content_hash[:2]
    directory.mkdir(parents=True, exist_ok=True)
    existing_path = next(directory.glob(f"{content_hash}.*"), None)
    if existing_path is None:
        extension = _extension_from_image_data(image)
        existing_path = directory / f"{content_hash}{extension}"
        _write_atomically(existing_path, image.data)

    return replace(
        image,
        content_hash=content_hash,
        path=str(existing_path),
    )
