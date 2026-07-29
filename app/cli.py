import argparse
import sys
import logging
from app.logging_setup import setup_logging
from app.pipeline import run
from app import config

logger = logging.getLogger("app.cli")


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
    except Exception:
        logger.exception("Pipeline çalıştırılırken hata oluştu.")
        sys.exit(1)

    for i, image in enumerate(results.images):
        file_name = f"{args.keyword}_{i}{image.extension}"  # burayı jpg den image extension yaptım çünkü content type değişebilir(png,jpeg vb)
        with open(file_name, "wb") as f:
            f.write(image.data)


if __name__ == "__main__":
    main()
