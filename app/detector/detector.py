# app/detector/detector.py

import logging
import threading
from io import BytesIO
from PIL import Image
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
    model = _get_or_load_model()
    try:
        pil_img = Image.open(BytesIO(image.data))

        with _model_lock:
            names = [keyword]
            model.set_classes(names, model.get_text_pe(names))
            results = list(model(pil_img, verbose=False))
        result = results[0]
        if not isinstance(result, Results):
            raise TypeError(f"Beklenmeyen model çıktı tipi: {type(result)}")
        boxes = result.boxes
        if boxes is None or boxes.conf is None or len(boxes.conf) == 0:
            max_conf = 0.0
        else:
            max_conf = float(boxes.conf.max().cpu().item())

        return DetectionResult(image=image, confidence=max_conf)

    except Exception:
        logger.exception("Görsel işlenirken hata oluştu.")
        return DetectionResult(image=image, confidence=0.0)
