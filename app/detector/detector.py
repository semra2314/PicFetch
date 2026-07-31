# app/detector/detector.py

import logging
import threading
from collections import OrderedDict
from io import BytesIO
from typing import Any

from PIL import Image, UnidentifiedImageError
from ultralytics import YOLOE
from ultralytics.engine.results import Results

from app import config
from app.domain import DownloadedImage, DetectionResult

logger = logging.getLogger(__name__)

_model: YOLOE | None = None
_model_lock = threading.RLock()
_TEXT_EMBEDDING_CACHE_SIZE = 128
_text_embedding_cache: OrderedDict[str, Any] = OrderedDict()
_embedding_cache_model: YOLOE | None = None


def _get_or_load_model() -> YOLOE:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("YOLOE-26 modeli belleğe yükleniyor...")
                _model = YOLOE(config.MODEL_NAME)
                logger.info("Model başarıyla yüklendi.")
    return _model


def _get_text_embedding_locked(model: YOLOE, keyword: str) -> Any:
    """Return the keyword embedding while ``_model_lock`` is held."""
    global _embedding_cache_model

    if _embedding_cache_model is not model:
        _text_embedding_cache.clear()
        _embedding_cache_model = model

    try:
        embedding = _text_embedding_cache.pop(keyword)
    except KeyError:
        embedding = model.get_text_pe([keyword])
        _text_embedding_cache[keyword] = embedding
        if len(_text_embedding_cache) > _TEXT_EMBEDDING_CACHE_SIZE:
            _text_embedding_cache.popitem(last=False)
    else:
        _text_embedding_cache[keyword] = embedding

    return embedding


def detect(image: DownloadedImage, keyword: str) -> DetectionResult:
    try:
        pil_img = Image.open(BytesIO(image.data))
        # PIL'in tembel decode işlemini burada tamamlamasını zorla.
        pil_img.load()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as e:
        logger.warning("Görsel decode edilemedi: %s", e)
        return DetectionResult(image=image, confidence=0.0)

    # Lazy model yükleme, embedding cache'i, keyword ayarı ve inference aynı
    # model durumu üzerinde birlikte çalışmalı.
    with _model_lock:
        model = _get_or_load_model()
        names = [keyword]
        embedding = _get_text_embedding_locked(model, keyword)
        model.set_classes(names, embedding)
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


def warm_up() -> None:
    """Load the model, text encoder, and inference path before serving requests."""
    buffer = BytesIO()
    with Image.new("RGB", (32, 32), color="white") as warmup_image:
        warmup_image.save(buffer, format="PNG")

    image = DownloadedImage(
        url="internal://warm-up.png",
        data=buffer.getvalue(),
        content_type="image/png",
    )
    logger.info("Model ısıtılıyor...")
    detect(image, "object")
    logger.info("Model ısıtma tamamlandı.")
