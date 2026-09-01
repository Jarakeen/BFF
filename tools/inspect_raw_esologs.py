from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.paths import RAW_DATA


FILES = [
    RAW_DATA / "esologs_probe.json",
    RAW_DATA / "esologs_night2.json",
]


def describe(value, indent=0, name="root"):
    prefix = " " * indent

    if isinstance(value, dict):
        print(f"{prefix}{name}: dict ({len(value)} keys)")

        for key, child in list(value.items())[:30]:
            describe(child, indent + 2, str(key))

        if len(value) > 30:
            print(
                f"{prefix}  ... "
                f"{len(value) - 30} more keys"
            )

    elif isinstance(value, list):
        print(f"{prefix}{name}: list ({len(value)} items)")

        if value:
            describe(value[0], indent + 2, "[0]")

    else:
        value_text = repr(value)

        if len(value_text) > 150:
            value_text = value_text[:147] + "..."

        print(
            f"{prefix}{name}: "
            f"{type(value).__name__} = {value_text}"
        )


def inspect_file(path: Path) -> None:
    print()
    print("=" * 80)
    print(path)
    print("=" * 80)

    if not path.exists():
        print("FILE DOES NOT EXIST")
        return

    size = path.stat().st_size

    print(f"Size: {size:,} bytes")

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            data = json.load(handle)

    except Exception as exc:
        print(f"ERROR READING JSON: {exc}")
        return

    print()
    print("TOP-LEVEL STRUCTURE")
    print("-" * 80)

    describe(data)


def main() -> None:
    for path in FILES:
        inspect_file(path)


if __name__ == "__main__":
    main()
