import argparse
from app.logging_setup import setup_logging
from app.pipeline import run


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", type=str)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    results = run(args.keyword, args.count)

    print(f"{results.found} adet görsel bulundu")

    for i, image in enumerate(results.images):
        file_name = f"{args.keyword}_{i}{image.extension}"  # burayı jpg den image extension yaptım çünkü content type değişebilir(png,jpeg vb)
        with open(file_name, "wb") as f:
            f.write(image.data)


if __name__ == "__main__":
    main()
