# bu dosyanın amacı gelen resim formatlarını  png, jpeg, webp vb. dönüştürmektir.

import io
import logging
from PIL import Image
from app.domain import DownloadedImage

logger = logging.getLogger(__name__)


class ImageConverter:
    """Görsel formatlarını birbirine dönüştürmek için kullanılan sınıf."""

    # Uzantı ve Content-Type eşleşmeleri
    CONTENT_TYPE_MAPPING = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/webp": "image/webp",
        "image/bmp": "image/bmp",
    }

    # Content-Type'tan PIL format ismine eşleşme
    PIL_FORMAT_MAPPING = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
        "image/bmp": "BMP",
    }

    @classmethod
    def convert(cls, image: DownloadedImage, target_format: str) -> DownloadedImage:
        """
        Bir DownloadedImage nesnesini belirtilen hedef formata dönüştürür.
        
        Args:
            image: Dönüştürülecek DownloadedImage nesnesi.
            target_format: Hedef format (örnek: 'png', '.png', 'image/png', 'webp', vb.).
            
        Returns:
            Dönüştürülmüş yeni bir DownloadedImage nesnesi (veya aynı format ise kendisi).
        """
        target_lower = target_format.strip().lower()
        
        # Hedef Content-Type'ı belirle
        content_type = cls.CONTENT_TYPE_MAPPING.get(target_lower)
        if not content_type:
            # Fallback/varsayılan tahminler
            if target_lower.startswith("image/"):
                content_type = target_lower
            elif target_lower.startswith("."):
                content_type = f"image/{target_lower[1:]}"
            else:
                content_type = f"image/{target_lower}"
        
        # PIL format ismini belirle (örn: JPEG, PNG, WEBP)
        pil_format = cls.PIL_FORMAT_MAPPING.get(content_type)
        if not pil_format:
            pil_format = content_type.split("/")[-1].upper()
            if pil_format == "JPG":
                pil_format = "JPEG"
                
        # Zaten aynı formatta ise dönüştürme yapma
        current_clean_type = image.content_type.split(";")[0].strip().lower()
        if current_clean_type == content_type:
            logger.debug("Görsel zaten hedef formatta (%s), dönüşüm atlanıyor.", content_type)
            return image

        try:
            pil_img = Image.open(io.BytesIO(image.data))
            
            # Şeffaflık (alpha channel) kontrolü. 
            # JPEG formatı şeffaflığı desteklemediği için RGBA veya LA modunu RGB'ye dönüştürmeliyiz.
            if pil_format == "JPEG" and pil_img.mode in ("RGBA", "LA", "P"):
                if pil_img.mode in ("RGBA", "LA"):
                    # Şeffaf kısımları beyaz arka planla kaplayalım
                    background = Image.new("RGB", pil_img.size, (255, 255, 255))
                    alpha = pil_img.split()[-1]
                    background.paste(pil_img, mask=alpha)
                    pil_img = background
                else:
                    pil_img = pil_img.convert("RGB")
            elif pil_img.mode not in ("RGB", "RGBA") and pil_format in ("PNG", "WEBP"):
                # Diğer formatlar için de uygun renk uzayına çekelim
                if pil_img.mode in ("P", "1"):
                    pil_img = pil_img.convert("RGBA")
            
            output_io = io.BytesIO()
            pil_img.save(output_io, format=pil_format)
            converted_data = output_io.getvalue()
            
            logger.info("Görsel formatı dönüştürüldü: %s -> %s", current_clean_type, content_type)
            return DownloadedImage(
                url=image.url,
                data=converted_data,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error("Görsel formatı dönüştürülürken hata oluştu: %s", e)
            # Hata durumunda orijinal görseli dön
            return image
