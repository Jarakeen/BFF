from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ID_PREFIX_RE = re.compile(r"^(\d+)_")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_collectibles(db_path: Path) -> dict[int, dict[str, str | int]]:
    if not db_path.is_file():
        raise FileNotFoundError(f"Collectibles database not found: {db_path}")

    with sqlite3.connect(db_path) as db:
        rows = db.execute(
            "SELECT id, name, COALESCE(icon, '') FROM collectible ORDER BY id"
        ).fetchall()

    return {
        int(row[0]): {
            "id": int(row[0]),
            "name": str(row[1] or ""),
            "original_icon": str(row[2] or ""),
        }
        for row in rows
    }


def _scan_icon_files(icon_dir: Path) -> tuple[dict[int, Path], list[Path], list[tuple[int, Path, Path]]]:
    by_id: dict[int, Path] = {}
    unrecognized: list[Path] = []
    duplicate_ids: list[tuple[int, Path, Path]] = []

    for path in sorted(icon_dir.iterdir()):
        if not path.is_file() or path.suffix.casefold() not in IMAGE_SUFFIXES:
            continue

        match = ID_PREFIX_RE.match(path.name)
        if match is None:
            unrecognized.append(path)
            continue

        collectible_id = int(match.group(1))
        previous = by_id.get(collectible_id)
        if previous is None:
            by_id[collectible_id] = path
            continue

        # Do not guess if two physical files claim the same collectible ID.
        duplicate_ids.append((collectible_id, previous, path))

    return by_id, unrecognized, duplicate_ids


def rebuild(data_dir: Path, *, dry_run: bool = False) -> dict[str, int]:
    data_dir = data_dir.resolve()
    db_path = data_dir / "eso.db"
    icon_dir = data_dir / "collectible_icons"
    manifest_path = icon_dir / "manifest.json"

    if not icon_dir.is_dir():
        raise FileNotFoundError(f"Icon directory not found: {icon_dir}")

    collectibles = _load_collectibles(db_path)
    files_by_id, unrecognized, duplicate_ids = _scan_icon_files(icon_dir)

    if duplicate_ids:
        sample = ", ".join(
            f"{cid}: {a.name} / {b.name}" for cid, a, b in duplicate_ids[:10]
        )
        raise RuntimeError(
            f"Found {len(duplicate_ids)} duplicate collectible IDs in filenames; "
            f"refusing to guess. First conflicts: {sample}"
        )

    entries: dict[str, dict] = {}
    unknown_ids: list[int] = []

    for collectible_id, path in sorted(files_by_id.items()):
        collectible = collectibles.get(collectible_id)
        if collectible is None:
            unknown_ids.append(collectible_id)
            continue

        digest = _sha256(path)
        entries[str(collectible_id)] = {
            "id": collectible_id,
            "name": collectible["name"],
            "file": path.name,
            "sha256": digest,
            "original_icon": collectible["original_icon"],
            "source_url": "",
            "source_html": "",
            "score": None,
            "manifest_rebuilt_from_filename": True,
        }

    image_count = sum(
        1
        for path in icon_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    )

    if image_count and not entries:
        raise RuntimeError(
            "Image files exist but no filename IDs matched collectibles in eso.db; refusing to write an empty manifest."
        )

    payload = {
        "version": 2,
        "database": db_path.name,
        "html_root": "",
        "icon_root": icon_dir.name,
        "collectible_count": len(collectibles),
        "matched_count": len(entries),
        "downloaded_count": len(entries),
        "failure_count": 0,
        "entries": entries,
        "failures": [],
        "manifest_rebuilt": True,
    }

    if not dry_run:
        if manifest_path.exists():
            backup_path = manifest_path.with_name("manifest.pre_rebuild.json")
            shutil.copy2(manifest_path, backup_path)

        temp_path = manifest_path.with_suffix(".json.tmp")
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp_path.replace(manifest_path)

    return {
        "database_collectibles": len(collectibles),
        "image_files": image_count,
        "recognized_filename_ids": len(files_by_id),
        "rebuilt_entries": len(entries),
        "unknown_ids": len(unknown_ids),
        "unrecognized_files": len(unrecognized),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild collectible_icons/manifest.json from existing ID-prefixed icon filenames."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = rebuild(args.data_dir, dry_run=args.dry_run)

    print("=" * 64)
    print(" Black Feather Foundry - Collectible Icon Manifest Repair")
    print("=" * 64)
    print(f"Collectibles in DB:      {result['database_collectibles']:,}")
    print(f"Image files found:       {result['image_files']:,}")
    print(f"Recognized filename IDs: {result['recognized_filename_ids']:,}")
    print(f"Manifest entries:        {result['rebuilt_entries']:,}")
    print(f"Unknown IDs:             {result['unknown_ids']:,}")
    print(f"Unrecognized images:     {result['unrecognized_files']:,}")
    print("Mode:                    " + ("DRY RUN - no files changed" if args.dry_run else "APPLIED"))
    if not args.dry_run:
        print("Backup:                  data/collectible_icons/manifest.pre_rebuild.json")


if __name__ == "__main__":
    main()
