from app.domain import Candidate
from ddgs import DDGS


def search(keyword: str, count: int) -> list[Candidate]:
    """Verilen arama kelimesiyle DuckDuckGo üzerinden görsel araması yapar
    ve belirlenen sayıda Candidate nesnesi döndürür."""

    results = DDGS().images(query=keyword, max_results=count)

    candidates = [Candidate(url=result["image"]) for result in results][:count]
    return candidates
