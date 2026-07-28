import hashlib
from dataclasses import replace
from pathlib import Path

from app import config
from app.domain import DownloadedImage


def save_image(image: DownloadedImage) -> DownloadedImage:
    content_hash = hashlib.sha256(image.data).hexdigest()
    directory = Path(config.DOWNLOADS_DIR) / content_hash[:2]
    directory.mkdir(parents=True, exist_ok=True)
    existing_path = next(directory.glob(f"{content_hash}.*"), None)
    if existing_path is None:
        existing_path = directory / f"{content_hash}{image.extension}"
        existing_path.write_bytes(image.data)

    return replace(
        image,
        content_hash=content_hash,
        path=str(existing_path),
    )
