from __future__ import annotations

"""Audit FoundryDock's release boundary before building a distributable executable.

This audit is intentionally repository-aware: development material may exist in source,
but only explicitly approved assets may enter the frozen application. Top-level data
files are reported separately until each has been classified for the release payload.
"""

import argparse
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "packaging" / "release_manifest.py"
SPEC_PATH = ROOT / "packaging" / "BFF.spec"
VERSION_PATH = ROOT / "app_version.py"
STATUS_PATH = ROOT / "RELEASE_STATUS.md"


def _load_manifest():
    spec = importlib.util.spec_from_file_location("foundrydock_release_manifest", MANIFEST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load release manifest: {MANIFEST_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _version() -> str:
    text = VERSION_PATH.read_text(encoding="utf-8")
    match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not match:
        raise RuntimeError("app_version.py does not define APP_VERSION")
    return match.group(1)


def _top_level_data_files() -> list[str]:
    data_root = ROOT / "data"
    if not data_root.is_dir():
        return []
    return sorted(
        path.name
        for path in data_root.iterdir()
        if path.is_file() and path.suffix.casefold() not in {".py", ".db"}
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-data",
        action="store_true",
        help="Fail while any top-level runtime data file remains unclassified.",
    )
    args = parser.parse_args(argv)

    manifest = _load_manifest()
    errors: list[str] = []
    warnings: list[str] = []

    version = _version()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"APP_VERSION must be semantic x.y.z, got {version!r}")

    if not STATUS_PATH.is_file():
        errors.append("RELEASE_STATUS.md is missing")

    approved_sources = [source for source, _destination in manifest.RUNTIME_ASSET_DATAS]
    for source, _destination in (*manifest.RUNTIME_ASSET_DATAS, *manifest.SEED_DATAS):
        if not (ROOT / source).exists():
            errors.append(f"Required release payload is missing: {source}")

    for forbidden in manifest.FORBIDDEN_RELEASE_ASSET_PREFIXES:
        for approved in approved_sources:
            if approved == forbidden or approved.startswith(forbidden.rstrip("/") + "/"):
                errors.append(f"Forbidden legacy asset is allowlisted: {approved}")

    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    if 'release_manifest.py' not in spec_text or 'pyinstaller_datas' not in spec_text:
        errors.append("BFF.spec is not consuming packaging/release_manifest.py")
    if '(str(project_root / "assets"), "assets")' in spec_text:
        errors.append("BFF.spec still bundles the entire assets tree")

    user_owned = set(manifest.USER_OWNED_DATA_FILES)
    runtime_external = set(getattr(manifest, "RUNTIME_EXTERNAL_DATA_FILES", ()))
    first_install = set(getattr(manifest, "CLEAN_FIRST_INSTALL_DATA_FILES", ()))
    classified = user_owned | runtime_external | first_install
    unclassified = [name for name in _top_level_data_files() if name not in classified]
    if unclassified:
        preview = ", ".join(unclassified[:30])
        more = len(unclassified) - min(len(unclassified), 30)
        suffix = f" (+{more} more)" if more else ""
        message = (
            f"{len(unclassified)} top-level data files are not release-classified yet: "
            f"{preview}{suffix}"
        )
        if args.strict_data:
            errors.append(message)
        else:
            warnings.append(message)

    print("FOUNDRYDOCK RELEASE CANDIDATE AUDIT")
    print(f"version={version}")
    print(f"approved_asset_entries={len(manifest.RUNTIME_ASSET_DATAS)}")
    print(f"seed_entries={len(manifest.SEED_DATAS)}")
    print(f"unclassified_top_level_data={len(unclassified)}")

    if warnings:
        print("\nWARNINGS")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\nFAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("\nPASS")
    if unclassified:
        print("  Asset boundary is clean; data classification remains an explicit release gate.")
    else:
        print("  Asset and top-level data release boundaries are classified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
