from app.domain import Candidate, DownloadedImage


def download(candidates: list[Candidate]) -> list[DownloadedImage]:
    """Her URL'yi indirir. İndirilemeyeni/gerçek görsel olmayanı ELER (listeye koymaz, LOGLAR).
    Yani dönen liste, girdiden kısa olabilir. Timeout ve retry sayısı config'ten gelir."""
    ...
