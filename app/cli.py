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

    for image in results.images:
        print(f"- {image.path}")


if __name__ == "__main__":
    main()
