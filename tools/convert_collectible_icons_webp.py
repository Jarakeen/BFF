from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QImageReader, QImageWriter


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


def _load_image(path: Path) -> QImage:
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise RuntimeError(f"Could not decode {path.name}: {reader.errorString()}")
    return image


def _rgba_bytes(image: QImage) -> bytes:
    converted = image.convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = converted.constBits()
    return bytes(ptr[: converted.sizeInBytes()])


def _encode_webp(image: QImage) -> bytes:
    payload = QByteArray()
    buffer = QBuffer(payload)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise RuntimeError("Could not open in-memory WebP buffer")

    writer = QImageWriter(buffer, b"webp")
    writer.setQuality(100)
    if not writer.write(image):
        raise RuntimeError(f"WebP encode failed: {writer.errorString()}")
    buffer.close()
    return bytes(payload)


def _decode_webp(data: bytes) -> QImage:
    payload = QByteArray(data)
    buffer = QBuffer(payload)
    if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError("Could not open in-memory WebP decode buffer")
    reader = QImageReader(buffer, b"webp")
    image = reader.read()
    if image.isNull():
        raise RuntimeError(f"WebP verification decode failed: {reader.errorString()}")
    buffer.close()
    return image


def _webp_supported() -> bool:
    formats = {bytes(fmt).decode("ascii", errors="ignore").casefold() for fmt in QImageWriter.supportedImageFormats()}
    return "webp" in formats


def optimize(icon_dir: Path, *, apply: bool = False) -> dict[str, int]:
    icon_dir = icon_dir.resolve()
    manifest_path = icon_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not _webp_supported():
        supported = ", ".join(sorted(bytes(fmt).decode("ascii", errors="ignore") for fmt in QImageWriter.supportedImageFormats()))
        raise RuntimeError(f"Qt WebP writer support is unavailable. Supported formats: {supported}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("entries", {})
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Manifest has no usable entries; refusing conversion")

    referenced: dict[str, Path] = {}
    entry_files: dict[str, str] = {}
    missing: list[str] = []

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
            missing.append(str(collectible_id))
            continue
        if path.suffix.casefold() not in IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported referenced image type: {path.name}")
        referenced[filename] = path
        entry_files[str(collectible_id)] = filename

    if missing:
        sample = ", ".join(missing[:10])
        raise FileNotFoundError(
            f"Manifest references {len(missing)} missing files; refusing conversion. First IDs: {sample}"
        )
    if not referenced:
        raise ValueError("Manifest contains no existing referenced image files")

    before_bytes = sum(path.stat().st_size for path in referenced.values())
    projected_bytes = before_bytes
    converted_files = 0
    already_webp = 0
    not_smaller = 0
    verified_identical = 0
    conversions: dict[str, tuple[str, bytes, str]] = {}

    for index, (filename, path) in enumerate(sorted(referenced.items()), 1):
        if path.suffix.casefold() == ".webp":
            already_webp += 1
            continue

        original_image = _load_image(path)
        webp_bytes = _encode_webp(original_image)
        roundtrip = _decode_webp(webp_bytes)

        if original_image.size() != roundtrip.size() or _rgba_bytes(original_image) != _rgba_bytes(roundtrip):
            raise RuntimeError(f"Pixel verification failed for {filename}; refusing conversion")

        verified_identical += 1
        original_size = path.stat().st_size
        if len(webp_bytes) >= original_size:
            not_smaller += 1
            continue

        target_name = f"{path.stem}.webp"
        if target_name in referenced and target_name != filename:
            raise RuntimeError(f"Target filename collision: {target_name}")

        digest = _sha256_bytes(webp_bytes)
        conversions[filename] = (target_name, webp_bytes, digest)
        converted_files += 1
        projected_bytes -= original_size - len(webp_bytes)

        if index % 1000 == 0:
            print(f"  inspected {index:,}/{len(referenced):,} icon files")

    if not apply:
        return {
            "referenced_files": len(referenced),
            "manifest_entries": len(entry_files),
            "converted_files": converted_files,
            "verified_identical": verified_identical,
            "already_webp": already_webp,
            "not_smaller": not_smaller,
            "before_bytes": before_bytes,
            "after_bytes": projected_bytes,
            "saved_bytes": max(0, before_bytes - projected_bytes),
        }

    staging_dir = icon_dir / ".webp_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        for old_name, (target_name, webp_bytes, _digest) in conversions.items():
            staged = staging_dir / target_name
            staged.write_bytes(webp_bytes)
            check = _load_image(staged)
            source = _load_image(icon_dir / old_name)
            if source.size() != check.size() or _rgba_bytes(source) != _rgba_bytes(check):
                raise RuntimeError(f"Staged pixel verification failed for {old_name}")

        backup_path = icon_dir / "manifest.pre_webp.json"
        shutil.copy2(manifest_path, backup_path)

        for old_name, (target_name, _webp_bytes, _digest) in conversions.items():
            target = icon_dir / target_name
            os.replace(staging_dir / target_name, target)

        for collectible_id, filename in entry_files.items():
            conversion = conversions.get(filename)
            if conversion is None:
                continue
            target_name, _webp_bytes, digest = conversion
            entry = entries[collectible_id]
            entry["file"] = target_name
            entry["sha256"] = digest

        temp_manifest = manifest_path.with_suffix(".json.tmp")
        temp_manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp_manifest, manifest_path)

        still_referenced = {
            str(entry.get("file", "") or "").strip()
            for entry in entries.values()
            if isinstance(entry, dict)
        }
        for old_name in conversions:
            if old_name not in still_referenced:
                old_path = icon_dir / old_name
                if old_path.is_file():
                    old_path.unlink()
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    after_bytes = sum(
        path.stat().st_size
        for path in icon_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES
    )
    return {
        "referenced_files": len(referenced),
        "manifest_entries": len(entry_files),
        "converted_files": converted_files,
        "verified_identical": verified_identical,
        "already_webp": already_webp,
        "not_smaller": not_smaller,
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "saved_bytes": max(0, before_bytes - after_bytes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert collectible icons to pixel-verified WebP only when the result is smaller."
    )
    parser.add_argument(
        "--icon-dir",
        type=Path,
        default=DEFAULT_ICON_DIR,
        help="Collectible icon cache directory. Defaults to data/collectible_icons.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply verified conversions. Without this flag, only report projected savings.",
    )
    args = parser.parse_args()

    print("=" * 64)
    print(" Black Feather Foundry - Collectible Icon WebP Optimizer")
    print("=" * 64)
    result = optimize(args.icon_dir, apply=args.apply)
    print(f"Referenced files:     {result['referenced_files']:,}")
    print(f"Manifest entries:     {result['manifest_entries']:,}")
    print(f"Pixel-verified:       {result['verified_identical']:,}")
    print(f"Files convertible:    {result['converted_files']:,}")
    print(f"Already WebP:         {result['already_webp']:,}")
    print(f"WebP not smaller:     {result['not_smaller']:,}")
    print(f"Before:               {_format_bytes(result['before_bytes'])}")
    print(f"After:                {_format_bytes(result['after_bytes'])}")
    print(f"Space saved:          {_format_bytes(result['saved_bytes'])}")
    print(f"Mode:                  {'APPLIED' if args.apply else 'DRY RUN - no files changed'}")
    if args.apply:
        print("Backup:                data/collectible_icons/manifest.pre_webp.json")


if __name__ == "__main__":
    main()
