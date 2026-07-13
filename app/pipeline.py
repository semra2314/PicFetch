from app.domain import DownloadedImage,Candidate, DetectionResult
from app.search.search import search
from app.detector.detector import detect
from app.downloader.downloader import download
from app.ranking.ranking import rank
from app.config import OVERFETCH,DETECT_THRESHOLD


def run(keyword: str, count: int) -> list[DownloadedImage]:
    candidates = search(keyword, count * OVERFETCH)
    results = []
    for candidate in candidates:
        downloaded = download([candidate])
        if not downloaded:
            continue
        image = downloaded[0]
        result = detect(image, keyword)
        results.append(result)
    return rank(results, DETECT_THRESHOLD, count)


def mock_search(keyword, count):
    return [Candidate(url="https://ornek.com/kedi.jpg"), Candidate(url="https://ornek.com/kedi2.jpg")] 

def mock_download(candidates):
    return [DownloadedImage(url=candidate.url, data=b"fake_image_data") for candidate in candidates]

def mock_detect(image, keyword):
    return DetectionResult(image=image, confidence=0.9)
    
def mock_rank(results, threshold, limit):
    return [result.image for result in results]

if __name__ == "__main__":
    search = mock_search
    download = mock_download
    detect = mock_detect
    rank = mock_rank
    result = run("kedi", 1)
    print(result)