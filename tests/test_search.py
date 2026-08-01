"""search fonksiyonunun 5 koşulda çalışıp çalışmadığı test edilmesi"""

from app.search.search import search
from app.domain import Candidate
from unittest.mock import call, patch  # swap testi call kullanıyor
from app import config
import logging

# normal durum
# sonucun 0 (boş) olması durumu
# hata oluşma (error) durumu
# recovery
# eksik anahtar


def test_search_normal():

    with patch("app.search.search.DDGS") as mock_ddgs:
        # gerçek DDGS servisini mock ile değiştirerek
        # dış bağımlılığı kaldırıyoruz

        mock_ddgs.return_value.__enter__.return_value.images.return_value = [
            {"image": "http://ornek.com/1.jpg"},
            {"image": "http://ornek.com/2.jpg"},
            {"image": "http://ornek.com/3.jpg"},
        ]
        result = search("cat", 3)  # Test edilen search() fonksiyonunu çağırıyoruz
        assert len(result) == 3
        assert isinstance(
            result[0], Candidate
        )  # İlk elemanın Candidate nesnesi olduğunu doğruluyoruz
        assert (
            result[0].url == "http://ornek.com/1.jpg"
        )  # İlk Candidate nesnesinin URL bilgisinin doğru olduğunu kontrol ediyoruz


def test_search_empty(caplog):
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.images.return_value = []
        with caplog.at_level(logging.WARNING):
            result = search("cat", 3)
        assert result == []  # dönen değer  boş liste mi diye kontrol eder
        assert "0 sonuç" in caplog.text


def test_search_error(caplog):
    with patch("app.search.search.DDGS") as mock_ddgs:
        with patch("app.search.search.time.sleep") as mock_sleep:
            mock_images = mock_ddgs.return_value.__enter__.return_value.images
            mock_images.side_effect = Exception("ağ hatası")
            with caplog.at_level(logging.ERROR):
                result = search("cat", 3)
            assert result == []
            assert mock_images.call_count == config.SEARCH_RETRIES
            assert mock_sleep.call_count == config.SEARCH_RETRIES - 1
            assert "failed" in caplog.text


def test_search_recovers():
    with patch("app.search.search.DDGS") as mock_ddgs:
        with patch("app.search.search.time.sleep") as mock_sleep:
            mock_images = mock_ddgs.return_value.__enter__.return_value.images
            mock_images.side_effect = [
                Exception("ağ hatası"),  # 1. deneme patlar
                [  # 2. deneme başarılı ve count'u doldurur
                    {"image": "http://ornek.com/1.jpg"},
                    {"image": "http://ornek.com/2.jpg"},
                    {"image": "http://ornek.com/3.jpg"},
                ],
            ]
            result = search("cat", 3)
            assert len(result) == 3
            assert result[0].url == "http://ornek.com/1.jpg"
            mock_sleep.assert_called_once()
            assert (
                mock_images.call_count == 2
            )  # call_count 2 kez denendi mi (1 patlama + 1 başarı)


def test_search_skips_missing_key(caplog):  # eksik anahtar atlanmalı durumu
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_ddgs.return_value.__enter__.return_value.images.return_value = [
            {"image": "http://ornek.com/1.jpg"},
            {},  # eksik anahtar atlandı
            {"image": "http://ornek.com/2.jpg"},
        ]
        with caplog.at_level(logging.WARNING):
            result = search("cat", 3)
        assert len(result) == 2
        assert "atlandı" in caplog.text


def test_search_swaps_when_min_greater_than_max(monkeypatch) -> None:
    monkeypatch.setattr(config, "SEARCH_RETRY_DELAY_MIN", 5)
    monkeypatch.setattr(config, "SEARCH_RETRY_DELAY_MAX", 2)
    with (
        patch("app.search.search.DDGS") as mock_ddgs,
        patch("app.search.search.time.sleep") as mock_sleep,
        patch("app.search.search.random.randint") as mock_randint,
    ):
        mock_ddgs.return_value.__enter__.return_value.images.side_effect = Exception(
            "DDGS error"
        )
        result = search("araba", 3)
        assert mock_randint.call_args_list == [call(2, 5)] * (config.SEARCH_RETRIES - 1)
        assert mock_sleep.call_count == config.SEARCH_RETRIES - 1
        assert result == []


def test_search_does_not_retry_parsing_errors() -> None:
    with (
        patch("app.search.search.DDGS") as mock_ddgs,
        patch("app.search.search.time.sleep") as mock_sleep,
    ):
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.return_value = [None]

        try:
            search("cat", 3)
        except AttributeError:
            pass
        else:
            raise AssertionError("Ayrıştırma hatası çağırana iletilmeliydi")

        mock_images.assert_called_once_with(
            query="cat",
            max_results=3,
            page=1,
            backend=config.SEARCH_BACKEND,
        )
        mock_sleep.assert_not_called()


# --- sayfalama ---


def test_search_uses_configured_backend(monkeypatch) -> None:
    """Motor seçimi koda gömülü değil, config'den okunur."""
    monkeypatch.setattr(config, "SEARCH_BACKEND", "bing")
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.return_value = [{"image": "http://ornek.com/1.jpg"}]
        search("cat", 1)

    mock_images.assert_called_once_with(
        query="cat", max_results=1, page=1, backend="bing"
    )


def test_search_paginates_until_count_reached(monkeypatch) -> None:
    """Tek sayfa count'u dolduramıyorsa sonraki sayfa istenir.

    Sayfalamanın var olma sebebi bu: ddgs max_results'ı motora iletmediği için
    sayfa başına sabit sayıda sonuç geliyor.
    """
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 3)
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.side_effect = [
            [{"image": "http://ornek.com/1.jpg"}, {"image": "http://ornek.com/2.jpg"}],
            [{"image": "http://ornek.com/3.jpg"}, {"image": "http://ornek.com/4.jpg"}],
        ]
        result = search("cat", 4)

    assert [candidate.url for candidate in result] == [
        "http://ornek.com/1.jpg",
        "http://ornek.com/2.jpg",
        "http://ornek.com/3.jpg",
        "http://ornek.com/4.jpg",
    ]
    # page artarak gitmeli; hep 1 gönderilirse aynı sayfa tekrar tekrar çekilir
    assert [c.kwargs["page"] for c in mock_images.call_args_list] == [1, 2]


def test_search_stops_as_soon_as_count_is_reached(monkeypatch) -> None:
    """count dolduğunda SEARCH_MAX_PAGES'e kadar devam edilmez."""
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 5)
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.return_value = [
            {"image": "http://ornek.com/1.jpg"},
            {"image": "http://ornek.com/2.jpg"},
        ]
        result = search("cat", 2)

    assert len(result) == 2
    mock_images.assert_called_once()


def test_search_deduplicates_urls_across_pages(monkeypatch) -> None:
    """Sayfalar arasında tekrar eden URL ikinci kez aday yapılmaz.

    pipeline zaten içerik hash'iyle tekilleştiriyor ama o indirmeden SONRA
    çalışıyor; burada elenen tekrar, hiç yapılmayan bir HTTP isteği demek.
    """
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 2)
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.side_effect = [
            [{"image": "http://ornek.com/1.jpg"}, {"image": "http://ornek.com/2.jpg"}],
            [{"image": "http://ornek.com/2.jpg"}, {"image": "http://ornek.com/3.jpg"}],
        ]
        result = search("cat", 10)

    assert [candidate.url for candidate in result] == [
        "http://ornek.com/1.jpg",
        "http://ornek.com/2.jpg",
        "http://ornek.com/3.jpg",
    ]


def test_search_stops_when_page_brings_nothing_new(monkeypatch, caplog) -> None:
    """Sayfa tamamen tekrardan ibaretse kaynak tükenmiştir, erken durulur."""
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 5)
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.return_value = [{"image": "http://ornek.com/1.jpg"}]
        with caplog.at_level(logging.INFO):
            result = search("cat", 10)

    assert len(result) == 1
    assert mock_images.call_count == 2  # 2. sayfa yeni sonuç getirmedi, durdu
    assert "sayfalama durduruldu" in caplog.text


def test_search_respects_max_pages(monkeypatch) -> None:
    """count dolmasa bile SEARCH_MAX_PAGES aşılmaz."""
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 2)
    with patch("app.search.search.DDGS") as mock_ddgs:
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.side_effect = [
            [{"image": "http://ornek.com/1.jpg"}],
            [{"image": "http://ornek.com/2.jpg"}],
        ]
        result = search("cat", 100)

    assert len(result) == 2
    assert mock_images.call_count == 2


def test_search_keeps_earlier_pages_when_later_page_fails(monkeypatch) -> None:
    """Retry sayfa başına çalışır: 2. sayfa tamamen çökse de 1. sayfa korunur.

    Retry tüm aramayı sarsaydı, geç gelen geçici bir hata o ana kadar
    toplanmış adayları da çöpe atardı.
    """
    monkeypatch.setattr(config, "SEARCH_MAX_PAGES", 3)
    with (
        patch("app.search.search.DDGS") as mock_ddgs,
        patch("app.search.search.time.sleep") as mock_sleep,
    ):
        mock_images = mock_ddgs.return_value.__enter__.return_value.images
        mock_images.side_effect = [
            [{"image": "http://ornek.com/1.jpg"}],  # 1. sayfa başarılı
            Exception("ağ hatası"),  # 2. sayfanın 3 denemesi de patlar
            Exception("ağ hatası"),
            Exception("ağ hatası"),
        ]
        result = search("cat", 10)

    assert [candidate.url for candidate in result] == ["http://ornek.com/1.jpg"]
    assert mock_sleep.call_count == config.SEARCH_RETRIES - 1
