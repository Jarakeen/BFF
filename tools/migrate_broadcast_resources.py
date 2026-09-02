from __future__ import annotations

import argparse
import base64
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.paths import BROADCAST_RESOURCES, DATA


RESOURCE_FILES = ("check.png", "blank.png")
_TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _copy_file(source: Path, destination: Path) -> bool:
    if not source.is_file() or destination.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _ensure_blank_resource(destination: Path) -> bool:
    """Create the transparent unchecked-state image if no legacy copy exists."""

    blank = destination / "blank.png"
    if blank.exists():
        return False
    blank.write_bytes(_TRANSPARENT_PNG)
    return True


def migrate(
    *,
    data_dir: Path = DATA,
    destination: Path = BROADCAST_RESOURCES,
) -> tuple[int, int]:
    """Copy local Broadcast visual resources out of core data without deleting them."""

    data_dir = Path(data_dir)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped = 0

    weather_source = data_dir / "Weather"
    weather_destination = destination / "Weather"
    if weather_source.is_dir():
        for source in weather_source.rglob("*"):
            if not source.is_file():
                continue
            target = weather_destination / source.relative_to(weather_source)
            if _copy_file(source, target):
                copied += 1
            else:
                skipped += 1

    for filename in RESOURCE_FILES:
        if _copy_file(data_dir / filename, destination / filename):
            copied += 1
        elif (data_dir / filename).exists():
            skipped += 1

    if _ensure_blank_resource(destination):
        copied += 1

    return copied, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy local OBS visual resources into the optional Broadcast module."
    )
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--destination", type=Path, default=BROADCAST_RESOURCES)
    args = parser.parse_args()

    copied, skipped = migrate(data_dir=args.data_dir, destination=args.destination)
    print("=" * 64)
    print(" BFF BROADCAST RESOURCE MIGRATION")
    print("=" * 64)
    print(f"Source:       {args.data_dir}")
    print(f"Destination:  {args.destination}")
    print(f"Copied:       {copied:,}")
    print(f"Preserved:    {skipped:,}")
    print("Legacy source files were not deleted.")


if __name__ == "__main__":
    main()
