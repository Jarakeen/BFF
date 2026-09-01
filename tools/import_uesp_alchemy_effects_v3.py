#!/usr/bin/env python3
"""
Black Feather Foundry
UESP Alchemy Effects Importer V3

Purpose
-------
Build one authoritative alchemy-effect dataset from the UESP pages that have
already been collected locally.

This version fixes the two problems from the previous importer:

1. Duplicate pages are merged safely even when an existing record already has
   source_files and no longer has source_file.
2. Completeness is based on EFFECT NAMES, not on the number of input files.
   Multiple pages for the same effect are merged instead of causing another
   effect to disappear.

The importer is deliberately database-safe:
    - default mode only reads raw files and writes a JSON output
    - --commit is reserved for a future DB import hook and currently does not
      modify eso.db

Expected raw location:
    research/raw/

The script recursively searches that directory for .html/.htm files and
also accepts JSON files containing previously parsed UESP effect records.

Usage
-----
    python tools/import_uesp_alchemy_effects_v3.py

Optional:
    python tools/import_uesp_alchemy_effects_v3.py --raw-dir research/raw
    python tools/import_uesp_alchemy_effects_v3.py --output research/processed/alchemy_effects.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.paths import PROCESSED, RAW_DATA

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: BeautifulSoup is required.")
    print("Install with: python -m pip install beautifulsoup4")
    raise


EXPECTED_EFFECTS = {
    # Core UESP Alchemy effects represented by the collected effect pages.
    "Breach",
    "Cowardice",
    "Defile",
    "Detection",
    "Enervation",
    "Entrapment",
    "Fracture",
    "Hindrance",
    "Increase Armor",
    "Increase Spell Power",
    "Increase Spell Resist",
    "Increase Weapon Power",
    "Invisible",
    "Lingering Health",
    "Maim",
    "Protection",
    "Ravage Health",
    "Restore Health",
    "Restore Magicka",
    "Restore Stamina",
    "Speed",
    "Spell Critical",
    "Uncertainty",
    "Unstoppable",
    "Vitality",
    "Weapon Critical",
    # Heroism was collected separately and should be accepted when present.
    "Heroism",
}

IGNORED_HTML_NAMES = {
    "online",
    "alchemy",
    "effects",
    "formulas",
    "uespwiki",
}

POTION_TIER_RE = re.compile(
    r"\b(?:Sip|Tincture|Dram|Potion|Solution|Elixir|Panacea|Distillate|Essence)\b",
    re.I,
)
POISON_TIER_RE = re.compile(
    r"\b(?:Poison|Traumatic|Sorcery-Draining|Disease-Draining|"
    r"Stamina-Draining|Magicka-Draining)\b",
    re.I,
)

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def norm_name(value: str) -> str:
    value = clean_text(value)
    value = value.replace("’", "'")
    return value.casefold()

def slugify(value: str) -> str:
    value = norm_name(value)
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value

def unique_preserve(values):
    seen = set()
    out = []
    for value in values:
        value = clean_text(value)
        if not value:
            continue
        key = norm_name(value)
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out

def add_unique_dict(items, item, key_fields):
    key = tuple(norm_name(item.get(field, "")) for field in key_fields)
    if not any(
        tuple(norm_name(existing.get(field, "")) for field in key_fields) == key
        for existing in items
    ):
        items.append(item)
        return True
    return False

def detect_effect_name_from_text(text: str) -> str | None:
    text = clean_text(text)

    for effect in sorted(EXPECTED_EFFECTS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(effect)}\b", text, re.I):
            return effect

    return None

def parse_table(table):
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        values = [clean_text(c.get_text(" ", strip=True)) for c in cells]
        values = [v for v in values if v]
        if values:
            rows.append(values)
    return rows

def classify_table(rows):
    joined = " ".join(" ".join(row) for row in rows[:5]).casefold()

    if "solvent" in joined and "potion" in joined:
        return "potion_tiers"
    if "solvent" in joined and "poison" in joined:
        return "poison_tiers"
    if "ingredients" in joined:
        return "formula"
    return None

def extract_reagents(soup) -> list[str]:
    reagents = []

    for table in soup.find_all("table"):
        rows = parse_table(table)
        joined = " ".join(" ".join(r) for r in rows[:8])

        if "availability" in joined.casefold():
            for a in table.find_all("a"):
                text = clean_text(a.get_text(" ", strip=True))
                if text and text.casefold() not in {
                    "click on any item for details"
                }:
                    reagents.append(text)

    if not reagents:
        for a in soup.find_all("a"):
            href = clean_text(a.get("href", ""))
            text = clean_text(a.get_text(" ", strip=True))
            if "/Online:" in href and text:
                if any(
                    token in href.casefold()
                    for token in (
                        "corn_flower", "lady", "violet", "columbine",
                        "dragon", "nirnroot", "nightshade", "wormwood",
                        "stinkhorn", "blessed", "bugloss", "mountain_flower",
                        "water_hyacinth", "butterfly", "spider", "emetic",
                        "luminous", "fleshfly", "imp_stool", "namira",
                        "scrib", "beetle", "mudcrab", "clam_gall",
                        "powdered_mother", "torchbug", "white_cap",
                        "chaurus", "crimson",
                    )
                ):
                    reagents.append(text)

    return unique_preserve(reagents)

def extract_effect_from_h1(soup) -> str | None:
    h1 = soup.find("h1")
    if not h1:
        return None

    text = clean_text(h1.get_text(" ", strip=True))
    text = re.sub(r"^Online\s*:\s*", "", text, flags=re.I)

    for effect in sorted(EXPECTED_EFFECTS, key=len, reverse=True):
        if norm_name(text) == norm_name(effect):
            return effect

    return detect_effect_name_from_text(text)

def extract_page_effect(soup, path: Path) -> str | None:
    effect = extract_effect_from_h1(soup)
    if effect:
        return effect

    title = soup.title
    if title:
        effect = detect_effect_name_from_text(title.get_text(" ", strip=True))
        if effect:
            return effect

    stem = re.sub(r"[_\-]+", " ", path.stem)
    return detect_effect_name_from_text(stem)

def parse_effect_page(path: Path) -> dict | None:
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"WARNING: could not read {path}: {exc}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    effect = extract_page_effect(soup, path)

    if not effect:
        return None

    record = {
        "effect_name": effect,
        "effect_slug": slugify(effect),
        "source_files": [path.name],
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
                if len(row) >= 3 and norm_name(row[0]) not in {
                    "solvent", "solvent level"
                }:
                    record["potion_tiers"].append({
                        "solvent": row[0],
                        "level": row[1] if len(row) > 1 else "",
                        "name": row[2] if len(row) > 2 else "",
                        "values": row[3:],
                    })

        elif kind == "poison_tiers":
            for row in rows:
                if len(row) >= 3 and norm_name(row[0]) not in {
                    "solvent", "solvent level"
                }:
                    record["poison_tiers"].append({
                        "solvent": row[0],
                        "level": row[1] if len(row) > 1 else "",
                        "name": row[2] if len(row) > 2 else "",
                        "values": row[3:],
                    })

        elif kind == "formula":
            for row in rows:
                if len(row) < 2:
                    continue
                lower = " ".join(row).casefold()
                if "ingredients" in lower and len(row) <= 4:
                    continue

                record["formulas"].append({
                    "ingredients": unique_preserve(row[:3]),
                    "effects": unique_preserve(row[3:]),
                })

    return record

def merge_records(records):
    merged = {}
    duplicate_sources = defaultdict(list)

    for record in records:
        key = norm_name(record["effect_name"])

        if key not in merged:
            merged[key] = {
                "effect_name": record["effect_name"],
                "effect_slug": slugify(record["effect_name"]),
                "source_files": [],
                "reagents": [],
                "potion_tiers": [],
                "poison_tiers": [],
                "formulas": [],
            }

        existing = merged[key]

        for source in record.get("source_files", []):
            if source not in existing["source_files"]:
                if existing["source_files"]:
                    duplicate_sources[key].append(source)
                existing["source_files"].append(source)

        existing["reagents"] = unique_preserve(
            existing["reagents"] + record.get("reagents", [])
        )

        for tier in record.get("potion_tiers", []):
            add_unique_dict(
                existing["potion_tiers"],
                tier,
                ("solvent", "name", "level"),
            )

        for tier in record.get("poison_tiers", []):
            add_unique_dict(
                existing["poison_tiers"],
                tier,
                ("solvent", "name", "level"),
            )

        for formula in record.get("formulas", []):
            ingredients = tuple(sorted(norm_name(x) for x in formula["ingredients"]))
            effects = tuple(sorted(norm_name(x) for x in formula["effects"]))
            key_formula = (ingredients, effects)

            exists = False
            for old in existing["formulas"]:
                old_key = (
                    tuple(sorted(norm_name(x) for x in old["ingredients"])),
                    tuple(sorted(norm_name(x) for x in old["effects"])),
                )
                if old_key == key_formula:
                    exists = True
                    break

            if not exists:
                existing["formulas"].append(formula)

    return merged, duplicate_sources

def load_json_records(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(data, dict):
        for key in ("effects", "records", "items", "alchemyEffects"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        return []

    records = []
    for item in data:
        if not isinstance(item, dict):
            continue

        name = (
            item.get("effect_name")
            or item.get("effectName")
            or item.get("name")
        )
        if not name:
            continue

        records.append({
            "effect_name": clean_text(name),
            "effect_slug": slugify(name),
            "source_files": unique_preserve(
                item.get("source_files", [])
                if isinstance(item.get("source_files"), list)
                else [item.get("source_file", "")]
            ),
            "reagents": unique_preserve(item.get("reagents", [])),
            "potion_tiers": item.get("potion_tiers", [])
                if isinstance(item.get("potion_tiers", []), list) else [],
            "poison_tiers": item.get("poison_tiers", [])
                if isinstance(item.get("poison_tiers", []), list) else [],
            "formulas": item.get("formulas", [])
                if isinstance(item.get("formulas", []), list) else [],
        })

    return records

def discover_inputs(raw_dir: Path):
    html_files = sorted(
        list(raw_dir.rglob("*.html")) + list(raw_dir.rglob("*.htm"))
    )

    html_files = [
        p for p in html_files
        if "alchemy_effects" not in p.name.casefold()
    ]

    json_files = sorted(raw_dir.rglob("*.json"))
    json_files = [
        p for p in json_files
        if any(
            token in p.name.casefold()
            for token in ("alchemy", "potion", "poison")
        )
        and "alchemy_effects" not in p.name.casefold()
    ]

    return html_files, json_files

def validate(merged):
    names = {record["effect_name"] for record in merged.values()}

    missing = sorted(
        EXPECTED_EFFECTS - names,
        key=str.casefold,
    )

    missing_non_optional = [x for x in missing if x != "Heroism"]

    return missing, missing_non_optional

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        default=None,
        help=f"Raw data directory. Defaults to {RAW_DATA}.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=f"Output JSON. Defaults to {PROCESSED / 'alchemy_effects.json'}.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Reserved flag. V3 does not modify eso.db.",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir).resolve() if args.raw_dir else RAW_DATA
    output = (
        Path(args.output).resolve()
        if args.output
        else PROCESSED / "alchemy_effects.json"
    )

    print("=" * 60)
    print(" Black Feather Foundry")
    print(" UESP Alchemy Effects Importer V3")
    print("=" * 60)
    print()
    print("Raw:", raw_dir)
    print("Output:", output)
    print()

    if args.commit:
        print("NOTE: --commit was supplied, but this V3 importer intentionally")
        print("does not modify eso.db. It only writes the validated JSON dataset.")
        print()

    if not raw_dir.exists():
        print(f"ERROR: raw directory does not exist: {raw_dir}")
        sys.exit(1)

    html_files, json_files = discover_inputs(raw_dir)

    print(f"HTML pages found: {len(html_files)}")
    print(f"Alchemy JSON candidates: {len(json_files)}")
    print()

    records = []
    unclassified = []

    for path in html_files:
        record = parse_effect_page(path)
        if record is None:
            unclassified.append(path.name)
            continue
        records.append(record)

    for path in json_files:
        for record in load_json_records(path):
            if record.get("effect_name"):
                records.append(record)

    merged, duplicate_sources = merge_records(records)

    missing, missing_non_optional = validate(merged)

    output.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": 3,
        "source": "UESP local collected pages",
        "effect_count": len(merged),
        "effects": sorted(
            merged.values(),
            key=lambda x: x["effect_name"].casefold(),
        ),
        "validation": {
            "expected_effects": sorted(EXPECTED_EFFECTS, key=str.casefold),
            "missing_effects": missing,
            "missing_non_optional": missing_non_optional,
            "unclassified_files": sorted(unclassified),
        },
    }

    output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 60)
    print(" UESP Alchemy Import Complete")
    print("=" * 60)
    print()
    print(f"HTML pages parsed:       {len(html_files):>5}")
    print(f"Effect records found:    {len(records):>5}")
    print(f"Unique effects:          {len(merged):>5}")
    print(f"Duplicate source pages:  {sum(len(v) for v in duplicate_sources.values()):>5}")
    print(f"Unclassified pages:       {len(unclassified):>5}")
    print()

    print("EFFECT INVENTORY")
    print("-" * 60)

    for effect in sorted(merged.values(), key=lambda x: x["effect_name"].casefold()):
        print(
            f"{effect['effect_name']:<24} "
            f"{len(effect['reagents']):>2} reagents  "
            f"{len(effect['potion_tiers']):>2} potion  "
            f"{len(effect['poison_tiers']):>2} poison  "
            f"{len(effect['formulas']):>3} formulas  "
            f"{len(effect['source_files']):>2} sources"
        )

    print()
    print("VALIDATION")
    print("-" * 60)

    if missing:
        print("Missing expected effects:")
        for name in missing:
            print("  -", name)
    else:
        print("Missing expected effects: NONE")

    if unclassified:
        print()
        print("Unclassified files:")
        for name in unclassified:
            print("  -", name)
    else:
        print("Unclassified files:       NONE")

    if duplicate_sources:
        print()
        print("Duplicate source pages:")
        for key, sources in sorted(duplicate_sources.items()):
            print(f"  {merged[key]['effect_name']}:")
            for source in sources:
                print(f"    - {source}")

    print()
    print("Output:")
    print(" ", output)
    print()
    print("STATUS:", "VALIDATION PASSED" if not missing_non_optional else "CHECK MISSING EFFECTS")
    print()

if __name__ == "__main__":
    main()
