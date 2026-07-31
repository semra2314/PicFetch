from app.domain import DownloadedImage, DetectionResult


def count_at_or_above_threshold(
    results: list[DetectionResult], threshold: float
) -> int:
    return sum(result.confidence >= threshold for result in results)


def rank(
    results: list[DetectionResult], threshold: float, limit: int
) -> list[DownloadedImage]:

    filtered = [r for r in results if r.confidence >= threshold]
    sorted_results = sorted(filtered, key=lambda r: r.confidence, reverse=True)

    return [r.image for r in sorted_results[:limit]]
