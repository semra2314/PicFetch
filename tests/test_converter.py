# bu dosyanın amacı : app/converter/converter.py dosyasındaki ImageConverter sınıfının testlerini yapmaktır.

import io
from PIL import Image
import pytest
from app.domain import DownloadedImage
from app.converter import ImageConverter


def _create_dummy_image(format_name: str, mode: str = "RGB", color=(255, 0, 0)) -> bytes:
    img = Image.new(mode, (10, 10), color)
    output = io.BytesIO()
    img.save(output, format=format_name)
    return output.getvalue()


def test_convert_jpeg_to_png():
    jpeg_data = _create_dummy_image("JPEG")
    image = DownloadedImage(
        url="http://test.com/img.jpg",
        data=jpeg_data,
        content_type="image/jpeg"
    )

    converted = ImageConverter.convert(image, "png")

    assert converted.content_type == "image/png"
    assert converted.extension == ".png"

    # Pillow ile okuyup formatın gerçekten PNG olduğunu doğrulayalım
    pil_img = Image.open(io.BytesIO(converted.data))
    assert pil_img.format == "PNG"


def test_convert_png_to_jpeg():
    png_data = _create_dummy_image("PNG")
    image = DownloadedImage(
        url="http://test.com/img.png",
        data=png_data,
        content_type="image/png"
    )

    converted = ImageConverter.convert(image, ".jpg")

    assert converted.content_type == "image/jpeg"
    assert converted.extension == ".jpg"

    pil_img = Image.open(io.BytesIO(converted.data))
    assert pil_img.format == "JPEG"


def test_convert_rgba_png_to_jpeg_removes_transparency():
    # Şeffaflık barındıran RGBA (Red, Green, Blue, Alpha) görseli
    rgba_data = _create_dummy_image("PNG", mode="RGBA", color=(255, 0, 0, 128))
    image = DownloadedImage(
        url="http://test.com/transparent.png",
        data=rgba_data,
        content_type="image/png"
    )

    # JPEG şeffaflığı desteklemez. ImageConverter bunu handle edip hata almadan dönüştürmeli.
    converted = ImageConverter.convert(image, "image/jpeg")

    assert converted.content_type == "image/jpeg"
    assert converted.extension == ".jpg"

    pil_img = Image.open(io.BytesIO(converted.data))
    assert pil_img.format == "JPEG"
    assert pil_img.mode == "RGB"  # Alpha kanalı temizlenmiş olmalı


def test_convert_same_format_returns_same_object():
    jpeg_data = _create_dummy_image("JPEG")
    image = DownloadedImage(
        url="http://test.com/img.jpg",
        data=jpeg_data,
        content_type="image/jpeg"
    )

    # Zaten JPEG formatında olan bir görseli tekrar JPEG yapmaya çalışıyoruz
    converted = ImageConverter.convert(image, "jpg")

    assert converted is image  # Aynı referans dönmeli, gereksiz işlem yapılmamalı


def test_convert_case_insensitive_and_normalization():
    png_data = _create_dummy_image("PNG")
    image = DownloadedImage(
        url="http://test.com/img.png",
        data=png_data,
        content_type="image/png"
    )

    converted = ImageConverter.convert(image, "  WeBP  ")

    assert converted.content_type == "image/webp"
    assert converted.extension == ".webp"

    pil_img = Image.open(io.BytesIO(converted.data))
    assert pil_img.format == "WEBP"


def test_convert_invalid_image_data_returns_original():
    # Geçersiz/bozuk görsel verisi
    image = DownloadedImage(
        url="http://test.com/img.png",
        data=b"not_an_image_data",
        content_type="image/png"
    )

    converted = ImageConverter.convert(image, "webp")

    # Hata yakalanmalı ve orijinal image geri dönmeli
    assert converted is image
