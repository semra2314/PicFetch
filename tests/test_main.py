from pathlib import Path

import pytest
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from starlette.routing import Mount

from app import config
from app.main import app

client = TestClient(app)


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
