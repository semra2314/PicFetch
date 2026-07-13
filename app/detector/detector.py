from app.domain import DownloadedImage, DetectionResult


def detect(image: DownloadedImage, keyword: str) -> DetectionResult:
    """YOLOE-26'ya `keyword`'ü metin komutu verip görseli tarar; en yüksek güven skorunu döndürür.
    Hiç bulamazsa confidence=0.0. Eşik kararı VERMEZ — o ranking'in işi.
    Not: DownloadedImage.data baytlarını modele vermeden önce PIL/ndarray'e çevirir.
    KRİTİK: Model ağırlıkları BİR KEZ, uygulama açılışında yüklenir (modül seviyesinde tutulur),
    her çağrıda yeniden yüklenmez (yoksa sistem felç olur). Ama keyword komutu (set_classes)
    HER çağrıda o aramanın kelimesiyle ayarlanır — çünkü set_classes önceki kelimenin üzerine yazar;
    her aramada yeniden set edilmezse önceki aramanın nesnesi aranmaya devam eder (araba/kedi karışması)."""
    ...
