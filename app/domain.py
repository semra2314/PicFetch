from dataclasses import dataclass

@dataclass
class Candidate:
    url: str
    source: str | None = None

@dataclass
class DownloadedImage:
    url: str
    data: bytes

@dataclass
class DetectionResult:
    image: DownloadedImage
    confidence: float