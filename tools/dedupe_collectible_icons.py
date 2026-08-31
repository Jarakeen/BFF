from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ICON_DIR = ROOT / "data" / "collectible_icons"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _folder_bytes(icon_dir: Path) -> int:
    total = 0
    for path in icon_dir.iterdir():
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES:
            total += path.stat().st_size
    return total


def _image_files(icon_dir: Path) -> list[Path]:
    return [
        path
        for path in icon_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    ]


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def dedupe(icon_dir: Path, *, dry_run: bool = False) -> dict[str, int]:
    icon_dir = icon_dir.resolve()
    manifest_path = icon_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        raise ValueError("Manifest entries must be an object")

    referenced_paths: dict[str, Path] = {}
    missing_entries: list[str] = []
    for collectible_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        filename = str(entry.get("file", "") or "").strip()
        if not filename:
            continue
        path = (icon_dir / filename).resolve()
        try:
            path.relative_to(icon_dir)
        except ValueError:
            raise ValueError(f"Manifest entry {collectible_id} escapes icon directory: {filename}")
        if not path.is_file():
            missing_entries.append(str(collectible_id))
            continue
        referenced_paths[filename] = path

    if missing_entries:
        sample = ", ".join(missing_entries[:10])
        raise FileNotFoundError(
            f"Manifest references {len(missing_entries)} missing files; refusing cleanup. "
            f"First IDs: {sample}"
        )

    image_files = _image_files(icon_dir)
    before_bytes = sum(path.stat().st_size for path in image_files)

    # Safety invariant: a populated cache with zero manifest references is not
    # a valid dedupe state. Without this guard the projected size would be zero,
    # which is not compression, merely an unusable manifest. Refuse both dry-run
    # and applied cleanup until the manifest has been repaired/rebuilt.
    if image_files and not referenced_paths:
        raise RuntimeError(
            "Collectible icon cache contains "
            f"{len(image_files):,} image files ({_format_bytes(before_bytes)}) but "
            "manifest.json contains zero usable file references. Refusing dedupe. "
            "Repair or rebuild the collectible icon manifest first."
        )

    digest_to_paths: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(set(referenced_paths.values())):
        digest_to_paths[_sha256(path)].append(path)

    canonical_for_digest: dict[str, str] = {}
    for digest, paths in digest_to_paths.items():
        suffix = paths[0].suffix.casefold()
        if suffix == ".jpeg":
            suffix = ".jpg"
        canonical_for_digest[digest] = f"{digest}{suffix}"

    rewritten_entries = 0
    old_referenced_files = set(referenced_paths)
    new_referenced_files: set[str] = set()

    for collectible_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        filename = str(entry.get("file", "") or "").strip()
        if not filename:
            continue
        source = referenced_paths.get(filename)
        if source is None:
            continue
        digest = _sha256(source)
        canonical_name = canonical_for_digest[digest]
        new_referenced_files.add(canonical_name)
        if filename != canonical_name or entry.get("sha256") != digest:
            rewritten_entries += 1
        entry["file"] = canonical_name
        entry["sha256"] = digest

    duplicate_files = max(0, len(old_referenced_files) - len(digest_to_paths))

    if dry_run:
        projected_bytes = sum(paths[0].stat().st_size for paths in digest_to_paths.values())
        return {
            "referenced_files": len(old_referenced_files),
            "unique_files": len(digest_to_paths),
            "duplicate_files": duplicate_files,
            "rewritten_entries": rewritten_entries,
            "before_bytes": before_bytes,
            "after_bytes": projected_bytes,
            "saved_bytes": max(0, before_bytes - projected_bytes),
        }

    # Create canonical files first. The manifest is not touched until every
    # canonical target exists, keeping the cache usable if a copy fails.
    for digest, paths in digest_to_paths.items():
        canonical_name = canonical_for_digest[digest]
        target = icon_dir / canonical_name
        if not target.exists():
            shutil.copy2(paths[0], target)

    temp_manifest = manifest_path.with_suffix(".json.tmp")
    temp_manifest.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temp_manifest, manifest_path)

    # Only delete files that the old manifest referenced and the new manifest
    # no longer references. Unrelated files are deliberately left alone.
    for filename in sorted(old_referenced_files - new_referenced_files):
        path = icon_dir / filename
        if path.is_file():
            path.unlink()

    after_bytes = _folder_bytes(icon_dir)
    return {
        "referenced_files": len(old_referenced_files),
        "unique_files": len(digest_to_paths),
        "duplicate_files": duplicate_files,
        "rewritten_entries": rewritten_entries,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "saved_bytes": max(0, before_bytes - after_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Losslessly deduplicate collectible icon files by SHA-256."
    )
    parser.add_argument(
        "--icon-dir",
        type=Path,
        default=DEFAULT_ICON_DIR,
        help="Collectible icon cache directory. Defaults to data/collectible_icons.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report expected savings without changing files or manifest.",
    )
    args = parser.parse_args()

    result = dedupe(args.icon_dir, dry_run=args.dry_run)

    print("=" * 64)
    print(" Black Feather Foundry - Collectible Icon Deduper")
    print("=" * 64)
    print(f"Referenced files:    {result['referenced_files']:,}")
    print(f"Unique icon files:   {result['unique_files']:,}")
    print(f"Duplicate files:     {result['duplicate_files']:,}")
    print(f"Manifest entries:    {result['rewritten_entries']:,} rewritten")
    print(f"Before:              {_format_bytes(result['before_bytes'])}")
    print(f"After:               {_format_bytes(result['after_bytes'])}")
    print(f"Space saved:         {_format_bytes(result['saved_bytes'])}")
    if args.dry_run:
        print("Mode:                 DRY RUN - no files changed")
    else:
        print("Mode:                 APPLIED")


if __name__ == "__main__":
    main()
