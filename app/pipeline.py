from app.domain import DownloadedImage


def run(keyword: str, count: int) -> list[DownloadedImage]:
    """Tüm zinciri kurar: config.OVERFETCH * count aday çek → indir → tespit et → sırala.
    Zincirin herhangi bir adımı boş dönerse: çökmeden boş sonuç döndürür (sebep loglanır).
    AKIŞ (streaming): Görselleri hepsini indirip biriktirip sonra işleme; teker teker
    'indir → tespit et → bırak' akışıyla işle. Böylece aynı anda bellekte tek görsel kalır
    (RAM'in asıl kaldıracı budur, bytes/path değil — bkz. Bölüm 13/madde 6)"""
    ...
