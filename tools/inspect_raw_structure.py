from pathlib import Path
import json


FILES = [
    Path("data/raw/esologs_probe.json"),
    Path("data/raw/esologs_night2.json"),
]


def summarize(value, name="root", indent=0):
    prefix = " " * indent

    if isinstance(value, dict):
        print(f"{prefix}{name}: dict [{len(value)} keys]")

        for key, child in value.items():
            if isinstance(child, (dict, list)):
                if isinstance(child, list):
                    print(
                        f"{prefix}  {key}: "
                        f"list [{len(child)} items]"
                    )
                else:
                    print(
                        f"{prefix}  {key}: "
                        f"dict [{len(child)} keys]"
                    )
            else:
                print(
                    f"{prefix}  {key}: "
                    f"{type(child).__name__} = {child!r}"
                )

    elif isinstance(value, list):
        print(
            f"{prefix}{name}: "
            f"list [{len(value)} items]"
        )

        if value:
            first = value[0]

            if isinstance(first, dict):
                print(
                    f"{prefix}  [0]: dict "
                    f"[{len(first)} keys]"
                )
                print(
                    f"{prefix}  [0] keys: "
                    f"{list(first.keys())}"
                )
            else:
                print(
                    f"{prefix}  [0]: "
                    f"{type(first).__name__} = {first!r}"
                )


def main():
    for path in FILES:
        print()
        print("=" * 80)
        print(path)
        print("=" * 80)

        if not path.exists():
            print("MISSING")
            continue

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = json.load(handle)

        summarize(data)


if __name__ == "__main__":
    main()