from app.domain import DownloadedImage, DetectionResult


def rank(
    results: list[DetectionResult], threshold: float, limit: int
) -> list[DownloadedImage]:
    """confidence >= threshold olanları alır, skora göre azalan sıralar, ilk `limit` taneyi döndürür."""
    ...
