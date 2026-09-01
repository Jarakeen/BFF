#!/usr/bin/env python3
"""Recover the U50 UESP Restore Magicka alchemy effect as supplementary raw JSON.

The historical V3 alchemy importer omitted ``Restore Magicka`` from its
EXPECTED_EFFECTS vocabulary, so a locally collected Restore Magicka HTML page
could not enter the processed corpus.  This targeted recovery fetches the one
missing UESP page, parses only source-visible table data, and writes the same
record shape that V3 already accepts from supplementary JSON.

It never modifies eso.db.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.import_uesp_alchemy_effects_v3 import (
    classify_table,
    extract_reagents,
    parse_table,
    unique_preserve,
)

DEFAULT_URL = "https://en.uesp.net/wiki/Online:Restore_Magicka"
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "alchemy_restore_magicka.recovery.json"
USER_AGENT = "BlackFeatherFoundry/1.0 (ESO data provenance recovery)"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_restore_magicka_html(html: str, *, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = _clean(soup.get_text(" ", strip=True)).casefold()
    if "restore magicka" not in page_text:
        raise ValueError("Fetched UESP page does not identify Restore Magicka")

    record: dict[str, Any] = {
        "effect_name": "Restore Magicka",
        "effect_slug": "restore_magicka",
        "source_files": [source_url],
        "reagents": extract_reagents(soup),
        "potion_tiers": [],
        "poison_tiers": [],
        "formulas": [],
    }

    for table in soup.find_all("table"):
        rows = parse_table(table)
        if not rows:
            continue
        kind = classify_table(rows)
        if kind == "potion_tiers":
            for row in rows:
                if len(row) >= 3 and _clean(row[0]).casefold() not in {"solvent", "solvent level"}:
                    record["potion_tiers"].append(
                        {
                            "solvent": row[0],
                            "level": row[1] if len(row) > 1 else "",
                            "name": row[2] if len(row) > 2 else "",
                            "values": row[3:],
                        }
                    )
        elif kind == "poison_tiers":
            for row in rows:
                if len(row) >= 3 and _clean(row[0]).casefold() not in {"solvent", "solvent level"}:
                    record["poison_tiers"].append(
                        {
                            "solvent": row[0],
                            "level": row[1] if len(row) > 1 else "",
                            "name": row[2] if len(row) > 2 else "",
                            "values": row[3:],
                        }
                    )
        elif kind == "formula":
            for row in rows:
                if len(row) < 2:
                    continue
                lower = " ".join(row).casefold()
                if "ingredients" in lower and len(row) <= 4:
                    continue
                record["formulas"].append(
                    {
                        "ingredients": unique_preserve(row[:3]),
                        "effects": unique_preserve(row[3:]),
                    }
                )

    if not record["potion_tiers"]:
        raise ValueError("Restore Magicka page yielded no potion tier evidence")
    return record


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def recover(*, url: str, output: Path) -> int:
    print("========================================")
    print(" UESP RESTORE MAGICKA SOURCE RECOVERY")
    print("========================================")
    print(f"Source: {url}")
    print(f"Output: {output}")
    print()

    try:
        html = fetch_html(url)
        record = parse_restore_magicka_html(html, source_url=url)
    except (requests.RequestException, ValueError) as exc:
        print(f"Recovery failed: {exc}")
        return 1

    payload = {
        "schema_version": 1,
        "source": "UESP targeted recovery",
        "scope": "Restore Magicka",
        "records": [record],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Recovered effect: Restore Magicka")
    print(f"Reagents:       {len(record['reagents'])}")
    print(f"Potion tiers:   {len(record['potion_tiers'])}")
    print(f"Poison tiers:   {len(record['poison_tiers'])}")
    print(f"Formulas:       {len(record['formulas'])}")
    print()
    print("Database unchanged.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover missing UESP Restore Magicka alchemy evidence")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    raise SystemExit(recover(url=args.url, output=args.output))
