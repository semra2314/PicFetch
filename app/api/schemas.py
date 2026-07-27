from pydantic import BaseModel, Field, field_validator
from app import config


class SearchRequest(BaseModel):
    """Kullanıcıdan gelen aramaları karşılayan ve doğrulayan model."""
    keyword: str = Field(min_length=1) # karakter uzunluğunun en az 1 olmasını zorunlu kılar
    count: int = Field(ge=1, le=config.MAX_COUNT) # count için alt ve üst sınır

    @field_validator("keyword")
    @classmethod
    def validate_whitespace(cls, v: str) -> str:
        """arama kelimesinin başındaki/sondaki gereksiz boşlukları kırpar.
        metnin sadece boşluk karakterlerinden ("   ") oluşmasını engeller.
        """
        cleaned = v.strip()

        if not cleaned:
            raise ValueError("Keyword sadece boşluklardan oluşamaz.")

        return cleaned


class ImageResult(BaseModel): 
    image_url: str | None = None # storage tamamlanana kadar boş kalacak, çünkü onu dolduracak veriyi o kart üretecek.
    source_url: str # görselin çekildiği orijinal sayfanın linki


class SearchResponse(BaseModel):
    """Arama işlemi tamamlandıktan sonra istemciye dönülecek yanıt yapısı."""
    images: list[ImageResult] # elde edilen görsellere ait liste
    requested: int # Kullanıcının istekte bulunduğu (count) değer
    found: int # İşlem sonucunda gerçekten bulunan/geçerli görsel sayısı
