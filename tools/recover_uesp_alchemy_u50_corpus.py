#!/usr/bin/env python3
"""Recover the full U50 UESP Alchemy effect-page corpus as raw HTML.

The local processed Alchemy JSON can be rebuilt only if the underlying effect
pages still exist.  This tool fetches the canonical UESP page for every effect
known to the historical V3 importer, validates the page identity from its H1,
and writes raw HTML plus a provenance manifest.

It never modifies eso.db or data/processed/alchemy_effects.json.  The recovered
HTML is deliberately fed back through the existing V3 parser so there remains
one authoritative HTML parser rather than a second crawler-specific parser.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.import_uesp_alchemy_effects_v3 import (
    EXPECTED_EFFECTS,
    extract_effect_from_h1,
    norm_name,
    slugify,
)

BASE_URL = "https://en.uesp.net/wiki/Online:{slug}"
DEFAULT_RAW_DIR = ROOT / "data" / "raw" / "alchemy_u50_recovery"
DEFAULT_MANIFEST = ROOT / "data" / "raw" / "alchemy_u50_recovery_manifest.json"
USER_AGENT = "BlackFeatherFoundry/1.0 (ESO U50 alchemy provenance recovery)"
OPTIONAL_EFFECTS = frozenset({"Heroism"})


def source_url(effect_name: str) -> str:
    slug = "_".join(str(effect_name).strip().split())
    return BASE_URL.format(slug=slug)


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def validate_effect_page(html: str, *, expected_effect: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    detected = extract_effect_from_h1(soup)
    if detected is None:
        raise ValueError("UESP page H1 did not resolve to a known Alchemy effect")
    if norm_name(detected) != norm_name(expected_effect):
        raise ValueError(
            f"UESP page identity mismatch: expected {expected_effect!r}, detected {detected!r}"
        )
    return detected


def recover_corpus(
    *,
    effects: Iterable[str],
    raw_dir: Path,
    manifest_path: Path,
    fetcher: Callable[[str], str] = fetch_html,
) -> tuple[dict, int]:
    requested = sorted({str(value).strip() for value in effects if str(value).strip()}, key=str.casefold)
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    required_failures: list[str] = []

    for effect_name in requested:
        url = source_url(effect_name)
        output = raw_dir / f"alchemy_u50_{slugify(effect_name)}.html"
        record = {
            "effect_name": effect_name,
            "source_url": url,
            "output": str(output.relative_to(ROOT)) if output.is_relative_to(ROOT) else str(output),
            "status": "failed",
            "detected_effect": None,
            "error": None,
        }

        try:
            html = fetcher(url)
            detected = validate_effect_page(html, expected_effect=effect_name)
            output.write_text(html, encoding="utf-8")
            record["status"] = "recovered"
            record["detected_effect"] = detected
        except (requests.RequestException, ValueError, OSError) as exc:
            record["error"] = str(exc)
            if effect_name not in OPTIONAL_EFFECTS:
                required_failures.append(effect_name)

        records.append(record)

    manifest = {
        "schema_version": 1,
        "source": "UESP Online Alchemy effect pages",
        "game_update_scope": "U50 historical recovery",
        "requested_count": len(requested),
        "recovered_count": sum(1 for item in records if item["status"] == "recovered"),
        "failed_count": sum(1 for item in records if item["status"] == "failed"),
        "required_failures": required_failures,
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest, 1 if required_failures else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover the complete U50 UESP Alchemy source corpus")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--effect",
        action="append",
        dest="effects",
        help="Recover only this effect; repeat for multiple effects. Defaults to the full V3 vocabulary.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    effects = args.effects or sorted(EXPECTED_EFFECTS, key=str.casefold)

    print("========================================")
    print(" UESP U50 ALCHEMY CORPUS RECOVERY")
    print("========================================")
    print(f"Raw output: {args.raw_dir}")
    print(f"Manifest:   {args.manifest}")
    print(f"Effects:    {len(effects)}")
    print()

    manifest, exit_code = recover_corpus(
        effects=effects,
        raw_dir=args.raw_dir,
        manifest_path=args.manifest,
    )

    for record in manifest["records"]:
        marker = "OK" if record["status"] == "recovered" else "FAIL"
        detail = record["detected_effect"] or record["error"] or "unknown"
        print(f"  [{marker}] {record['effect_name']}: {detail}")

    print()
    print(f"Recovered: {manifest['recovered_count']}/{manifest['requested_count']}")
    if manifest["required_failures"]:
        print("Required failures: " + ", ".join(manifest["required_failures"]))
    elif manifest["failed_count"]:
        print("Only optional effects failed; core U50 corpus recovery is complete.")
    else:
        print("All requested effect pages recovered and identity-validated.")
    print("Database unchanged.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
