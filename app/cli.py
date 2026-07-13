import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", type=str)
    parser.add_argument("--count", type=str, default=10)
    args = parser.parse_args()
    print(f"keyword={args.keyword}, count={args.count}")


if __name__ == "__main__":
    main()
