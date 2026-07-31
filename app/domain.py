from dataclasses import dataclass


@dataclass
class Candidate:
    url: str
    source: str | None = None


@dataclass
class DownloadedImage:
    url: str
    data: bytes
    # aşağıya uygun dosya uzantısı vermezsem ne olur ? --- > her resmin sonuna .jpg yazar ama resim png ise görüntü bozulur veya açılmaz
    content_type: str = "image/jpeg"
    content_hash: str | None = None
    path: str | None = None

    @property
    def extension(self) -> str:
        """Content-Type bilgisine göre uygun dosya uzantısını döner (örneğin '.jpg', '.png')."""
        if not self.content_type:
            return ".jpg"
        clean_type = self.content_type.split(";")[0].strip().lower()
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
        }
        return mapping.get(clean_type, ".jpg")


@dataclass
class DetectionResult:
    image: DownloadedImage
    confidence: float


@dataclass
class PipelineResult:
    images: list[DownloadedImage]
    requested: int
    found: int
