from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.paths import NORMALIZED, PROCESSED, RAW_DATA


LEGACY_PATHS = {
    "raw": "data/raw",
    "processed": "data/processed",
    "normalized": "data/normalized",
}

CANONICAL_PATHS = {
    "raw": RAW_DATA,
    "processed": PROCESSED,
    "normalized": NORMALIZED,
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".ps1",
    ".bat",
    ".spec",
}

SKIP_DIR_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dist",
}

# These directories contain source/research payloads rather than code that
# resolves repository paths. Scanning them would produce huge amounts of
# irrelevant text and can be very expensive for ESO Logs exports.
SKIP_PATH_PREFIXES = (
    REPO_ROOT / "research" / "raw",
    REPO_ROOT / "research" / "processed",
    REPO_ROOT / "research" / "normalized",
    REPO_ROOT / "data" / "raw",
    REPO_ROOT / "data" / "processed",
    REPO_ROOT / "data" / "normalized",
    REPO_ROOT / "data" / "backup",
)


@dataclass(frozen=True)
class Inventory:
    exists: bool
    files: int
    bytes: int


def _under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def inventory(path: Path) -> Inventory:
    if not path.exists():
        return Inventory(False, 0, 0)

    files = 0
    total_bytes = 0
    for root, dirs, names in os.walk(path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
        root_path = Path(root)
        for name in names:
            item = root_path / name
            try:
                stat = item.stat()
            except OSError:
                continue
            if item.is_file():
                files += 1
                total_bytes += stat.st_size

    return Inventory(True, files, total_bytes)


def format_size(value: int) -> str:
    size = float(value)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{value} B"


def iter_text_files():
    for root, dirs, names in os.walk(REPO_ROOT):
        root_path = Path(root)
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIP_DIR_NAMES
            and not any(_under(root_path / name, prefix) for prefix in SKIP_PATH_PREFIXES)
        ]

        for name in names:
            path = root_path / name
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(_under(path, prefix) for prefix in SKIP_PATH_PREFIXES):
                continue
            yield path


def legacy_references() -> list[tuple[str, int, str]]:
    matches: list[tuple[str, int, str]] = []

    variants = set(LEGACY_PATHS.values())
    variants.update(value.replace("/", "\\") for value in LEGACY_PATHS.values())

    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        relative = path.relative_to(REPO_ROOT).as_posix()
        for line_number, line in enumerate(text.splitlines(), 1):
            if not any(value in line for value in variants):
                continue
            matches.append((relative, line_number, line.strip()))

    return matches


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit for migrating developer data from data/{raw,processed,normalized} "
            "to research/{raw,processed,normalized}."
        )
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when legacy path references remain.",
    )
    args = parser.parse_args()

    print("=" * 78)
    print(" RESEARCH DATA PATH MIGRATION AUDIT - READ ONLY")
    print("=" * 78)
    print(f"repo: {REPO_ROOT}")
    print()

    print("=== DIRECTORY INVENTORY ===")
    for key, legacy_text in LEGACY_PATHS.items():
        legacy = REPO_ROOT / legacy_text
        canonical = CANONICAL_PATHS[key]
        old = inventory(legacy)
        new = inventory(canonical)
        print(f"{key}:")
        print(
            f"  old  {legacy.relative_to(REPO_ROOT)} | exists={old.exists} "
            f"files={old.files} size={format_size(old.bytes)}"
        )
        print(
            f"  new  {canonical.relative_to(REPO_ROOT)} | exists={new.exists} "
            f"files={new.files} size={format_size(new.bytes)}"
        )
    print()

    matches = legacy_references()
    print("=== LEGACY PATH REFERENCES ===")
    if not matches:
        print("  (none)")
    else:
        for path, line_number, line in matches:
            print(f"  {path}:{line_number}: {line}")
    print()
    print(f"legacy reference count: {len(matches)}")
    print("No files or database rows were changed.")

    if args.strict and matches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
