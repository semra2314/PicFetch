import argparse
import sys
import logging
from app.logging_setup import setup_logging
from app.pipeline import run
from app import config

# Modül seviyesinde logger tanımlaması
logger = logging.getLogger(__name__)


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", type=str)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()

    if args.count < 1:
        parser.error("İstenen görsel sayısı 1'den küçük olamaz.")
    if args.count > config.MAX_COUNT:
        parser.error(
            f"İstenen görsel sayısı sistem sınırını ({config.MAX_COUNT}) aşıyor."
        )

    try:
        results = run(args.keyword, args.count)

        for i, image in enumerate(results.images):
            file_name = f"{args.keyword}_{i}{image.extension}"
            with open(file_name, "wb") as f:
                f.write(image.data)
    except ValueError as e:
        print(f"Girdi Hatası: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception:
        logger.exception(
            "İşlem sırasında veya dosyalar kaydedilirken beklenmeyen bir hata oluştu."
        )
        print(
            "Sistemde beklenmeyen bir hata oluştu. Lütfen logları kontrol edin.",
            file=sys.stderr,
        )
        sys.exit(1)

    if results.found == 0:
        print("Bu kelime için görsel bulunamadı.")
    elif results.found < results.requested:
        print(f"{results.requested} adet istendi fakat {results.found} adet bulundu")
    else:
        print("İstenilen sayıda bulundu")


if __name__ == "__main__":
    main()
