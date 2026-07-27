# app/detector/detector.py

import logging
import threading
from io import BytesIO

from PIL import Image, UnidentifiedImageError
from ultralytics import YOLOE
from ultralytics.engine.results import Results

from app.domain import DownloadedImage, DetectionResult

logger = logging.getLogger(__name__)

_model: YOLOE | None = None
_model_lock = threading.Lock()


def _get_or_load_model() -> YOLOE:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("YOLOE-26 modeli belleğe yükleniyor...")
                _model = YOLOE("yoloe-26m-seg.pt")
                logger.info("Model başarıyla yüklendi.")
    return _model


def detect(image: DownloadedImage, keyword: str) -> DetectionResult:
    try:
        pil_img = Image.open(BytesIO(image.data))
        # PIL'in tembel decode işlemini burada tamamlamasını zorla.
        pil_img.load()
    except (UnidentifiedImageError, OSError) as e:
        logger.warning("Görsel decode edilemedi: %s", e)
        return DetectionResult(image=image, confidence=0.0)

    # Yüklemeyi kilitli inference bloğuna almak deadlock oluşturabilir.
    model = _get_or_load_model()

    # Keyword ayarı ve inference aynı model durumu üzerinde birlikte çalışmalı.
    with _model_lock:
        names = [keyword]
        model.set_classes(names, model.get_text_pe(names))
        results = model(pil_img, verbose=False)

    # Ultralytics'in geniş dönüş tipini çalışma zamanında doğrula.
    assert isinstance(results, list) and results, (
        "Model boş veya beklenmeyen türde sonuç döndürdü."
    )

    first_result = results[0]
    assert isinstance(first_result, Results), (
        "Model sonucunun ilk elemanı Results nesnesi değil."
    )

    boxes = first_result.boxes
    conf = None if boxes is None else boxes.conf

    # Hem Tensor hem ndarray ile ortak çalışan işlemleri kullan.
    if conf is None or len(conf) == 0:
        max_conf = 0.0
    else:
        max_conf = float(conf.max())

    return DetectionResult(image=image, confidence=max_conf)
