from app.detector import detector
from app.domain import DownloadedImage
from PIL import Image
from io import BytesIO
from unittest.mock import MagicMock


def _gecerli_gorsel_baytlari():
    img = Image.new("RGB", (10, 10), color="green")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_detect_resets_keyword_each_call(monkeypatch):
    fake_model = MagicMock()
    calls = []
    fake_model.set_classes.side_effect = lambda names, *args: calls.append(names)
    fake_model.return_value = [
        MagicMock(boxes=MagicMock(conf=MagicMock(numel=lambda: 0)))
    ]
    monkeypatch.setattr(detector, "_model", fake_model)
    dummy_image = DownloadedImage(
        url="http://ornek.com/1.jpg", data=_gecerli_gorsel_baytlari()
    )
    detector.detect(dummy_image, "kedi")
    detector.detect(dummy_image, "araba")
    assert calls == [["kedi"], ["araba"]]


def test_detect_with_corrupted_image_returns_zero(caplog):
    corrupted_image = b"bu bir resim verisi degildir."
    fake_image = DownloadedImage(url="http://ornek.com/bozuk.jpg", data=corrupted_image)
    result = detector.detect(fake_image, "kedi")
    assert result.confidence == 0.0
    assert "Görsel işlenirken hata oluştu." in caplog.text
