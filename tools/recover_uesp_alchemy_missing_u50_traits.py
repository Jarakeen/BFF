#!/usr/bin/env python3
"""Recover U50 Alchemy effect pages omitted by the historical V3 vocabulary.

The original V3 expected-effect set did not include Timidity, Ravage Magicka,
or Ravage Stamina even though the recovered formula tables reference them as
real craftable Alchemy traits. V3 already accepts supplementary parsed JSON,
so this tool recovers those three UESP pages into that existing input shape
without modifying eso.db or introducing a competing processed-data pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.import_uesp_alchemy_effects_v3 import (
    classify_table,
    extract_reagents,
    parse_table,
    slugify,
    unique_preserve,
)

MISSING_U50_TRAITS = (
    "Ravage Magicka",
    "Ravage Stamina",
    "Timidity",
)
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "alchemy_u50_missing_traits.recovery.json"
BASE_URL = "https://en.uesp.net/wiki/Online:{slug}"
USER_AGENT = "BlackFeatherFoundry/1.0 (ESO U50 alchemy omitted-trait recovery)"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def source_url(effect_name: str) -> str:
    return BASE_URL.format(slug="_".join(str(effect_name).strip().split()))


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def _page_effect_name(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 is None:
        return ""
    text = _clean(h1.get_text(" ", strip=True))
    return re.sub(r"^Online\s*:\s*", "", text, flags=re.I).strip()


def parse_effect_html(html: str, *, expected_effect: str, source: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    detected = _page_effect_name(soup)
    if detected.casefold() != expected_effect.casefold():
        raise ValueError(
            f"UESP page identity mismatch: expected {expected_effect!r}, detected {detected!r}"
        )

    record: dict[str, Any] = {
        "effect_name": expected_effect,
        "effect_slug": slugify(expected_effect),
        "source_files": [source],
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

    if not record["potion_tiers"] and not record["poison_tiers"]:
        raise ValueError(f"{expected_effect} page yielded no potion or poison tier evidence")
    return record


def recover(
    *,
    effects: tuple[str, ...],
    output: Path,
    fetcher: Callable[[str], str] = fetch_html,
) -> tuple[dict[str, Any], int]:
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for effect_name in effects:
        url = source_url(effect_name)
        try:
            records.append(parse_effect_html(fetcher(url), expected_effect=effect_name, source=url))
        except (requests.RequestException, ValueError, OSError) as exc:
            failures.append({"effect_name": effect_name, "source_url": url, "error": str(exc)})

    payload: dict[str, Any] = {
        "schema_version": 1,
        "source": "UESP targeted U50 omitted-trait recovery",
        "scope": list(effects),
        "records": records,
        "failures": failures,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload, 1 if failures else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recover U50 Alchemy traits omitted by historical V3")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    print("========================================")
    print(" UESP U50 OMITTED ALCHEMY TRAIT RECOVERY")
    print("========================================")
    print(f"Output: {args.output}")
    print()

    payload, exit_code = recover(effects=MISSING_U50_TRAITS, output=args.output)
    recovered = {row["effect_name"]: row for row in payload["records"]}
    failures = {row["effect_name"]: row for row in payload["failures"]}
    for effect_name in MISSING_U50_TRAITS:
        if effect_name in recovered:
            row = recovered[effect_name]
            print(
                f"  [OK] {effect_name}: reagents={len(row['reagents'])} "
                f"potion={len(row['potion_tiers'])} poison={len(row['poison_tiers'])} "
                f"formulas={len(row['formulas'])}"
            )
        else:
            print(f"  [FAIL] {effect_name}: {failures[effect_name]['error']}")

    print()
    print(f"Recovered: {len(payload['records'])}/{len(MISSING_U50_TRAITS)}")
    print("Database unchanged.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
