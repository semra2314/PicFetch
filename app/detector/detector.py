# app/detector/detector.py

from app.domain import DownloadedImage, DetectionResult
from PIL import Image
from io import BytesIO
from ultralytics import YOLOE
# TODO: Gerekli kütüphaneleri (PIL, io, ultralytics) import et.

# TODO: Modelin sadece bir kez yüklenmesini sağlayacak global bir değişken veya yapı kur.
_model: YOLOE | None = None
def _get_or_load_model() -> YOLOE:
    global _model
    if _model is None:
        _model = YOLOE("yoloe_26.pt")
    return _model

def detect(image: DownloadedImage, keyword: str) -> DetectionResult:
    pil_img = Image.open(BytesIO(image.data))
    model = _get_or_load_model()
    model.set_classes([keyword])
    results = model(pil_img, verbose=False)
    boxes = results[0].boxes
    if len(boxes) == 0:
        max_conf = 0.0
    else:
        max_conf = float(max(boxes.conf))
    return DetectionResult(image=image, confidence=max_conf)    
    # 1. image.data içindeki baytları al.
    # 2. Bu baytları io.BytesIO ile okuyup PIL Image nesnesine çevir.
    # 3. Global modeli çağır.
    # 4. Modelin arayacağı kelimeyi (keyword) modele set et (önceki kelimenin üstüne yazsın).
    # 5. PIL görselini modele verip tahmin (inference) yaptır.
    # 6. Sonuçlar içinden güven (confidence) skorunu çek. Bulamazsa 0.0 yap.
    # 7. DetectionResult nesnesini oluştur (içine image ve confidence koyarak) ve döndür.
