from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "data" / "collectible_icons"
DEFAULT_DESTINATION = ROOT / "content_packs" / "collectible_icons"


def migrate(source: Path, destination: Path) -> tuple[int, int]:
    """Copy an existing collectible icon cache into the optional pack location.

    Existing destination files are preserved. The legacy source is never
    deleted by this migration, making the operation safe to repeat and easy to
    verify before retiring the old cache.
    """

    source = Path(source)
    destination = Path(destination)
    if not source.is_dir():
        raise FileNotFoundError(f"Legacy collectible icon cache not found: {source}")

    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0

    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped += 1
            continue
        shutil.copy2(path, target)
        copied += 1

    return copied, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy the legacy collectible thumbnail cache into its optional content pack."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    args = parser.parse_args()

    copied, skipped = migrate(args.source, args.destination)
    print("=" * 64)
    print(" BFF COLLECTIBLE THUMBNAIL PACK MIGRATION")
    print("=" * 64)
    print(f"Source:       {args.source}")
    print(f"Destination:  {args.destination}")
    print(f"Copied:       {copied:,}")
    print(f"Preserved:    {skipped:,}")
    print("Legacy source was not deleted.")


if __name__ == "__main__":
    main()
