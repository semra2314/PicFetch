from app.detector import detector
from app.domain import DownloadedImage
from PIL import Image
from io import BytesIO
from unittest.mock import MagicMock, call
from ultralytics.engine.results import Results


def _gecerli_gorsel_baytlari():
    img = Image.new("RGB", (10, 10), color="green")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _fake_model() -> MagicMock:
    fake_model = MagicMock()
    fake_result = MagicMock(spec=Results)
    fake_result.boxes = None
    fake_model.return_value = [fake_result]
    return fake_model


def test_detect_resets_keyword_each_call(monkeypatch) -> None:
    fake_model = MagicMock()
    calls = []
    fake_model.set_classes.side_effect = lambda names, *args: calls.append(names)

    fake_result = MagicMock(spec=Results)
    fake_result.boxes = None
    fake_model.return_value = [fake_result]

    monkeypatch.setattr(detector, "_model", fake_model)

    dummy_image = DownloadedImage(
        url="http://ornek.com/1.jpg",
        data=_gecerli_gorsel_baytlari(),
    )

    detector.detect(dummy_image, "kedi")
    detector.detect(dummy_image, "köpek")

    assert calls == [["kedi"], ["köpek"]]


def test_detect_with_corrupted_image_returns_zero(caplog):
    corrupted_image = b"bu bir resim verisi degildir."
    fake_image = DownloadedImage(url="http://ornek.com/bozuk.jpg", data=corrupted_image)
    result = detector.detect(fake_image, "kedi")
    assert result.confidence == 0.0
    assert "Görsel decode edilemedi" in caplog.text


def test_detect_reuses_embedding_for_same_keyword(monkeypatch) -> None:
    fake_model = _fake_model()
    embedding = object()
    fake_model.get_text_pe.return_value = embedding
    monkeypatch.setattr(detector, "_model", fake_model)
    image = DownloadedImage(
        url="http://ornek.com/1.jpg",
        data=_gecerli_gorsel_baytlari(),
    )

    detector.detect(image, "kedi")
    detector.detect(image, "kedi")

    fake_model.get_text_pe.assert_called_once_with(["kedi"])
    assert fake_model.set_classes.call_args_list == [
        call(["kedi"], embedding),
        call(["kedi"], embedding),
    ]


def test_detect_caches_different_keywords_independently(monkeypatch) -> None:
    fake_model = _fake_model()
    fake_model.get_text_pe.side_effect = lambda names: f"embedding:{names[0]}"
    monkeypatch.setattr(detector, "_model", fake_model)
    image = DownloadedImage(
        url="http://ornek.com/1.jpg",
        data=_gecerli_gorsel_baytlari(),
    )

    detector.detect(image, "kedi")
    detector.detect(image, "köpek")
    detector.detect(image, "kedi")

    assert fake_model.get_text_pe.call_args_list == [call(["kedi"]), call(["köpek"])]
    assert fake_model.set_classes.call_count == 3


def test_detect_embedding_cache_uses_lru_eviction(monkeypatch) -> None:
    fake_model = _fake_model()
    fake_model.get_text_pe.side_effect = lambda names: f"embedding:{names[0]}"
    monkeypatch.setattr(detector, "_model", fake_model)
    image = DownloadedImage(
        url="http://ornek.com/1.jpg",
        data=_gecerli_gorsel_baytlari(),
    )

    for index in range(detector._TEXT_EMBEDDING_CACHE_SIZE):
        detector.detect(image, f"keyword-{index}")

    detector.detect(image, "keyword-0")
    detector.detect(image, f"keyword-{detector._TEXT_EMBEDDING_CACHE_SIZE}")
    detector.detect(image, "keyword-0")
    detector.detect(image, "keyword-1")

    calls = fake_model.get_text_pe.call_args_list
    assert calls.count(call(["keyword-0"])) == 1
    assert calls.count(call(["keyword-1"])) == 2
    assert len(detector._text_embedding_cache) == detector._TEXT_EMBEDDING_CACHE_SIZE


def test_detect_clears_embedding_cache_when_model_changes(monkeypatch) -> None:
    first_model = _fake_model()
    first_embedding = object()
    first_model.get_text_pe.return_value = first_embedding
    monkeypatch.setattr(detector, "_model", first_model)
    image = DownloadedImage(
        url="http://ornek.com/1.jpg",
        data=_gecerli_gorsel_baytlari(),
    )

    detector.detect(image, "kedi")

    second_model = _fake_model()
    second_embedding = object()
    second_model.get_text_pe.return_value = second_embedding
    monkeypatch.setattr(detector, "_model", second_model)

    detector.detect(image, "kedi")

    first_model.get_text_pe.assert_called_once_with(["kedi"])
    second_model.get_text_pe.assert_called_once_with(["kedi"])
    second_model.set_classes.assert_called_once_with(["kedi"], second_embedding)
