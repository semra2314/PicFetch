from app.domain import DetectionResult, DownloadedImage
from app.ranking.ranking import count_at_or_above_threshold, rank


def test_below_threshold_results_are_filtered_out():
    low = DetectionResult(
        image=DownloadedImage(url="http//ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.1,
    )
    result = rank([low], threshold=0.25, limit=5)
    assert result == []


def test_results_sorted_descending_by_confidence():
    low = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.25,
    )
    high = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/2.jpg", data=b"dummyjpg"),
        confidence=0.75,
    )
    result = rank([low, high], threshold=0.25, limit=5)
    assert result[0].url == high.image.url
    assert result[1].url == low.image.url


def test_limit_truncates_results():
    a = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.3,
    )
    b = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/2.jpg", data=b"dummyjpg"),
        confidence=0.5,
    )
    c = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/3.jpg", data=b"dummyjpg"),
        confidence=0.7,
    )
    result = rank([a, b, c], threshold=0.25, limit=2)
    assert len(result) == 2
    assert result[0].url == c.image.url
    assert result[1].url == b.image.url


def test_empty_input_returns_empty_list():
    empty_input = []
    ranked = rank(empty_input, threshold=0.25, limit=2)
    assert ranked == []


def test_equal_confidence_preserves_input_order():
    a = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.4,
    )
    b = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/2.jpg", data=b"dummyjpg"),
        confidence=0.4,
    )
    result = rank([a, b], threshold=0.25, limit=5)
    assert result[0].url == a.image.url
    assert result[1].url == b.image.url


def test_confidence_equal_to_threshold_is_included():
    a = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.25,
    )
    result = rank([a], threshold=0.25, limit=5)
    assert len(result) == 1


def test_count_at_or_above_threshold_includes_equal_confidence():
    below = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/1.jpg", data=b"dummyjpg"),
        confidence=0.24,
    )
    equal = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/2.jpg", data=b"dummyjpg"),
        confidence=0.25,
    )
    above = DetectionResult(
        image=DownloadedImage(url="http://ornek.com/3.jpg", data=b"dummyjpg"),
        confidence=0.75,
    )

    result = count_at_or_above_threshold([below, equal, above], threshold=0.25)

    assert result == 2


def test_count_at_or_above_threshold_is_not_limited_by_rank_limit():
    results = [
        DetectionResult(
            image=DownloadedImage(
                url=f"http://ornek.com/{index}.jpg",
                data=b"dummyjpg",
            ),
            confidence=0.5,
        )
        for index in range(3)
    ]

    passing_count = count_at_or_above_threshold(results, threshold=0.25)
    ranked = rank(results, threshold=0.25, limit=2)

    assert passing_count == 3
    assert len(ranked) == 2


def test_count_at_or_above_threshold_returns_zero_for_empty_input():
    assert count_at_or_above_threshold([], threshold=0.25) == 0
