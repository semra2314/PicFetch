from app.domain import Candidate


def search(keyword: str, count: int) -> list[Candidate]:
    """Kelimeyle ilgili en fazla count aday URL döndürür.
    Kaynak patlarsa: retry sonrası hâlâ başarısızsa boş liste döndürür (exception fırlatmaz),
    AMA neden başarısız olduğunu LOGLAR."""
    ...
