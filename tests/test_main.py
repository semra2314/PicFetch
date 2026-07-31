from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.routing import Mount

from app import config, main as main_module
from app.main import app

client = TestClient(app)


def test_lifespan_warms_model_once(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_warm_up = MagicMock()
    monkeypatch.setattr(main_module, "warm_up", mock_warm_up)

    with TestClient(app) as lifespan_client:
        response = lifespan_client.get("/health")

    assert response.status_code == 200
    mock_warm_up.assert_called_once_with()


def test_root_returns_503_when_frontend_not_built(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build alınmamışken arayüz isteği anlaşılır bir hata döndürmeli.

    FRONTEND_DIST boş bir dizine yönlendiriliyor; index.html bulunamadığı
    için endpoint 503 vermeli. Bu, sunucunun çökmek yerine "build al"
    diyerek ayakta kaldığını doğrular.
    """
    monkeypatch.setattr(config, "FRONTEND_DIST", tmp_path / "yok")

    response = client.get("/")

    assert response.status_code == 503


def test_root_serves_index_when_frontend_built(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build varsa kök adres index.html'i HTML olarak sunmalı."""
    index_file = tmp_path / "index.html"
    index_file.write_text("<html><body>PicFetch</body></html>", encoding="utf-8")
    monkeypatch.setattr(config, "FRONTEND_DIST", tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "PicFetch" in response.text


def test_no_staticfiles_mounted_at_root() -> None:
    """Kök adrese StaticFiles mount edilmemeli.

    Edilseydi /search dâhil tüm API route'ları gölgelenirdi. Starlette
    "/" yolunu boş dizgeye normalize ettiği için ikisini de kontrol
    ediyoruz.
    """
    for route in app.routes:
        if isinstance(route, Mount) and isinstance(route.app, StaticFiles):
            assert route.path not in ("", "/")


def test_static_mount_exists() -> None:
    """İndirilen görseller /static altında sunulmaya devam etmeli."""
    mount_paths = {route.path for route in app.routes if isinstance(route, Mount)}

    assert "/static" in mount_paths


def test_static_response_has_immutable_cache_headers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    static_mount = next(
        route
        for route in app.routes
        if isinstance(route, Mount) and route.path == "/static"
    )
    assert isinstance(static_mount.app, StaticFiles)
    monkeypatch.setattr(static_mount, "app", StaticFiles(directory=tmp_path))
    (tmp_path / "image.jpg").write_bytes(b"image-bytes")

    response = client.get("/static/image.jpg")

    assert response.status_code == 200
    assert response.headers["cache-control"] == ("public, max-age=31536000, immutable")
    assert response.headers["x-content-type-options"] == "nosniff"


def test_api_response_does_not_have_static_cache_headers() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "immutable" not in response.headers.get("cache-control", "")
    assert "x-content-type-options" not in response.headers


def test_assets_mount_exists_regardless_of_build() -> None:
    """Build olmasa bile /assets mount'u kurulmuş olmalı.

    Koşullu mount edilseydi, sunucu çalışırken build alındığında /
    200 döner ama CSS/JS 404 verirdi; kullanıcı hatasız bir beyaz
    sayfa görürdü. Mount koşulsuz olduğu için bu test ortamdan
    bağımsız olarak deterministik.
    """
    mount_paths = {route.path for route in app.routes if isinstance(route, Mount)}

    assert "/assets" in mount_paths
