from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QImageReader


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ICON_DIR = ROOT / "data" / "collectible_icons"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _format_bytes(value: int) -> str:
    units = ("B", "KB", "MB", "GB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{value} B"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encode_image(image: QImage, suffix: str) -> bytes:
    fmt = suffix.casefold().lstrip(".")
    if fmt == "jpg" or fmt == "jpeg":
        qt_format = b"JPG"
        quality = 95
    elif fmt == "webp":
        qt_format = b"WEBP"
        quality = 95
    else:
        qt_format = b"PNG"
        quality = -1

    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise RuntimeError("Could not open in-memory image buffer")
    try:
        if not image.save(buffer, qt_format.data().decode("ascii"), quality):
            raise RuntimeError(f"Could not encode image as {qt_format.data().decode('ascii')}")
    finally:
        buffer.close()
    return bytes(byte_array)


def _load_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise RuntimeError(reader.errorString() or "Qt could not decode image")
    return image


def _resized_bytes(path: Path, max_size: int) -> tuple[bytes, tuple[int, int], tuple[int, int], bool]:
    image = _load_image(path)
    original_size = (image.width(), image.height())

    if image.width() <= max_size and image.height() <= max_size:
        return path.read_bytes(), original_size, original_size, False

    scaled = image.scaled(
        max_size,
        max_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        raise RuntimeError("Qt returned an empty resized image")

    encoded = _encode_image(scaled, path.suffix)
    return encoded, original_size, (scaled.width(), scaled.height()), True


def optimize(icon_dir: Path, *, max_size: int = 128, apply: bool = False) -> dict:
    if max_size < 112:
        raise ValueError("max-size must be at least 112 because the Collectibles detail view is 112x112")

    icon_dir = icon_dir.resolve()
    manifest_path = icon_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", {})
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Manifest has no collectible icon entries; refusing optimization")

    referenced: dict[str, list[str]] = {}
    for collectible_id, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        filename = str(entry.get("file", "") or "").strip()
        if not filename:
            continue
        referenced.setdefault(filename, []).append(str(collectible_id))

    if not referenced:
        raise ValueError("Manifest contains no usable icon filenames; refusing optimization")

    missing = [name for name in referenced if not (icon_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(
            f"Manifest references {len(missing)} missing icon files; refusing optimization. "
            f"First: {', '.join(missing[:5])}"
        )

    unsupported = [name for name in referenced if Path(name).suffix.casefold() not in IMAGE_SUFFIXES]
    if unsupported:
        raise ValueError(
            f"Manifest references {len(unsupported)} unsupported image types; refusing optimization. "
            f"First: {', '.join(unsupported[:5])}"
        )

    before_bytes = 0
    projected_bytes = 0
    resized_files = 0
    unchanged_files = 0
    failures: list[tuple[str, str]] = []
    replacements: dict[str, bytes] = {}
    dimensions: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}

    for index, filename in enumerate(sorted(referenced), 1):
        path = icon_dir / filename
        before_bytes += path.stat().st_size
        try:
            encoded, old_size, new_size, resized = _resized_bytes(path, max_size)
        except Exception as exc:
            failures.append((filename, str(exc)))
            continue

        dimensions[filename] = (old_size, new_size)
        projected_bytes += len(encoded)
        if resized:
            resized_files += 1
            replacements[filename] = encoded
        else:
            unchanged_files += 1

        if index % 1000 == 0:
            print(f"  inspected {index:,}/{len(referenced):,} icon files")

    if failures:
        sample = "; ".join(f"{name}: {error}" for name, error in failures[:5])
        raise RuntimeError(
            f"Could not safely process {len(failures)} icon files; no changes made. First failures: {sample}"
        )

    result = {
        "files": len(referenced),
        "resized": resized_files,
        "unchanged": unchanged_files,
        "before_bytes": before_bytes,
        "after_bytes": projected_bytes,
        "saved_bytes": max(0, before_bytes - projected_bytes),
        "max_size": max_size,
        "entries": len(entries),
    }

    if not apply:
        return result

    backup_manifest = icon_dir / "manifest.pre_resize.json"
    if not backup_manifest.exists():
        shutil.copy2(manifest_path, backup_manifest)

    staging_dir = icon_dir / ".resize_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        for filename, encoded in replacements.items():
            staged = staging_dir / filename
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(encoded)
            check = _load_image(staged)
            if check.width() > max_size or check.height() > max_size:
                raise RuntimeError(f"Validation failed for resized icon: {filename}")

        for filename, encoded in replacements.items():
            target = icon_dir / filename
            staged = staging_dir / filename
            os.replace(staged, target)
            digest = _sha256_bytes(encoded)
            for collectible_id in referenced.get(filename, []):
                entry = entries.get(collectible_id)
                if isinstance(entry, dict):
                    entry["sha256"] = digest

        payload["icon_max_size"] = max_size
        payload["icon_resize_mode"] = "keep_aspect_ratio_smooth"
        temp_manifest = manifest_path.with_suffix(".json.tmp")
        temp_manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp_manifest, manifest_path)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resize collectible icon cache to a UI-appropriate maximum dimension."
    )
    parser.add_argument(
        "--icon-dir",
        type=Path,
        default=DEFAULT_ICON_DIR,
        help="Collectible icon directory. Defaults to data/collectible_icons.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=128,
        help="Maximum width/height in pixels. Default: 128. Minimum: 112.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually replace oversized images after staging and validation. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()

    print("=" * 64)
    print(" Black Feather Foundry - Collectible Icon Resize Optimizer")
    print("=" * 64)
    print(f"Target maximum:       {args.max_size}x{args.max_size}")

    result = optimize(args.icon_dir, max_size=args.max_size, apply=args.apply)

    print(f"Referenced files:     {result['files']:,}")
    print(f"Manifest entries:     {result['entries']:,}")
    print(f"Files resized:        {result['resized']:,}")
    print(f"Already small enough: {result['unchanged']:,}")
    print(f"Before:               {_format_bytes(result['before_bytes'])}")
    print(f"After:                {_format_bytes(result['after_bytes'])}")
    print(f"Space saved:          {_format_bytes(result['saved_bytes'])}")
    print("Mode:                  APPLIED" if args.apply else "Mode:                  DRY RUN - no files changed")
    if args.apply:
        print("Manifest backup:       data/collectible_icons/manifest.pre_resize.json")


if __name__ == "__main__":
    main()
