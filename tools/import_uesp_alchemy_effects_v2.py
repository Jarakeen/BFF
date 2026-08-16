#!/usr/bin/env python3
"""
Black Feather Foundry
UESP Crafted Alchemy Effect Page Importer

Stage 1 importer: HTML -> normalized JSON.

- Scans a directory of saved UESP Online:Alchemy effect HTML pages.
- Extracts effect identity, reagent availability, potion/poison tiers,
  and formula tables.
- Deduplicates repeated pages and repeated formula rows.
- Does NOT modify eso.db.

Expected input:
    data/raw/uesp/alchemy_effects/*.htm

Output:
    data/processed/uesp_alchemy_effects.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "uesp" / "alchemy_effects"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "uesp_alchemy_effects.json"


def clean(value: str | None) -> str:
    if not value:
        return ""
    value = value.replace("\xa0", " ")
    return " ".join(value.split()).strip()


def normalize(value: str) -> str:
    value = clean(value).casefold()
    value = value.replace("’", "'").replace("‘", "'")
    return value


def link_name(cell: Tag | None) -> str:
    if cell is None:
        return ""
    # Prefer visible wiki link text over icon alt text.
    links = cell.find_all("a")
    for link in links:
        text = clean(link.get_text(" ", strip=True))
        if text:
            return text
    return clean(cell.get_text(" ", strip=True))


def cell_value(cell: Tag | None) -> str:
    return clean(cell.get_text(" ", strip=True)) if cell else ""


def parse_level(value: str) -> int | None:
    m = re.search(r"(-?\d+)", value)
    return int(m.group(1)) if m else None


def parse_float(value: str) -> float | None:
    m = re.search(r"(-?\d+(?:\.\d+)?)", value)
    return float(m.group(1)) if m else None


def parse_infobox(soup: BeautifulSoup) -> tuple[str, str, list[str]]:
    heading = soup.find("h1", class_="firstHeading")
    title = clean(heading.get_text(" ", strip=True)) if heading else ""
    effect_name = title.split(":", 1)[1].strip() if ":" in title else title

    effect_type = ""
    reagents: list[str] = []

    infobox = soup.find("table", class_="infobox")
    if infobox:
        rows = infobox.find_all("tr")
        availability_pending = False
        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            row_text = normalize(row.get_text(" ", strip=True))
            if "availability" in row_text and len(cells) == 1:
                availability_pending = True
                continue
            if availability_pending:
                for a in row.find_all("a"):
                    name = clean(a.get_text(" ", strip=True))
                    if name and not name.startswith("File:"):
                        reagents.append(name)
                availability_pending = False
                continue
            if len(cells) >= 2:
                label = normalize(cells[0].get_text(" ", strip=True))
                if label == "type":
                    effect_type = cell_value(cells[1])

    return effect_name, effect_type, sorted(set(reagents), key=normalize)


def parse_descriptions(soup: BeautifulSoup) -> dict[str, str]:
    result = {"potion": "", "poison": ""}
    for p in soup.find_all("p"):
        text = clean(p.get_text(" ", strip=True))
        if text.lower().startswith("potion description:"):
            result["potion"] = text[len("Potion description:"):].strip()
        elif text.lower().startswith("poison description:"):
            result["poison"] = text[len("Poison description:"):].strip()
    return result


def table_headers(table: Tag) -> list[str]:
    first = table.find("tr")
    if not first:
        return []
    return [clean(th.get_text(" ", strip=True)).lower() for th in first.find_all("th")]


def parse_tier_table(table: Tag, kind: str) -> list[dict[str, Any]]:
    headers = table_headers(table)
    if not headers or "solvent" not in headers:
        return []

    rows: list[dict[str, Any]] = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue

        solvent = link_name(cells[0]) or cell_value(cells[0])
        level = parse_level(cell_value(cells[1]))
        item_name = link_name(cells[2]) or cell_value(cells[2])
        duration = parse_float(cell_value(cells[3]))
        triple_duration = parse_float(cell_value(cells[4])) if len(cells) >= 5 else None

        if not solvent or not item_name:
            continue

        rows.append({
            "kind": kind,
            "solvent": solvent,
            "level": level,
            "name": item_name,
            "duration": duration,
            "triple_duration": triple_duration,
        })
    return rows


def parse_effect_tables(soup: BeautifulSoup) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    potions: list[dict[str, Any]] = []
    poisons: list[dict[str, Any]] = []

    effects_heading = soup.find(id="Effects")
    if not effects_heading:
        return potions, poisons

    for kind in ("potion", "poison"):
        heading = None
        for h in effects_heading.find_all_next("h3"):
            if normalize(h.get_text(" ", strip=True)).startswith(kind):
                heading = h
                break
        if not heading:
            continue
        table = heading.find_next("table", class_="wikitable")
        if not table:
            continue
        rows = parse_tier_table(table, kind)
        if kind == "potion":
            potions.extend(rows)
        else:
            poisons.extend(rows)

    return potions, poisons


def parse_formula_table(table: Tag, section: str) -> list[dict[str, Any]]:
    headers = table_headers(table)
    if not headers:
        return []

    rows: list[dict[str, Any]] = []
    for tr in table.find_all("tr")[1:]:
        cells = tr.find_all("td")
        if not cells:
            continue

        names = [link_name(c) for c in cells]
        if section == "single_effect":
            ingredients = [n for n in names if n]
            if len(ingredients) >= 2:
                rows.append({
                    "section": section,
                    "ingredients": sorted(ingredients[:2], key=normalize),
                    "additional_effects": [],
                })
        elif section == "triple_ingredient_and_second_effect":
            if len(names) >= 4 and all(names[:3]):
                rows.append({
                    "section": section,
                    "ingredients": sorted(names[:3], key=normalize),
                    "additional_effects": [names[3]] if names[3] else [],
                })
        elif section == "two_effects":
            if len(names) >= 4 and all(names[:2]) and names[2]:
                rows.append({
                    "section": section,
                    "ingredients": sorted(names[:3], key=normalize),
                    "additional_effects": [names[3]] if names[3] else [],
                })
        elif section == "three_effects":
            if len(names) >= 5 and all(names[:3]):
                effects = [n for n in names[3:] if n]
                rows.append({
                    "section": section,
                    "ingredients": sorted(names[:3], key=normalize),
                    "additional_effects": effects,
                })

    return rows


def parse_formulas(soup: BeautifulSoup) -> list[dict[str, Any]]:
    formulas: list[dict[str, Any]] = []
    section_ids = {
        "Single_Effect": "single_effect",
        "Triple_Ingredient_and_Second_Effect": "triple_ingredient_and_second_effect",
        "Two_Effects": "two_effects",
        "Three_Effects": "three_effects",
        "Triple_Effect": "triple_effect",
    }

    formulas_heading = soup.find(id="Formulas")
    if not formulas_heading:
        return formulas

    for heading_id, section in section_ids.items():
        heading = soup.find(id=heading_id)
        if not heading:
            continue
        for node in heading.find_all_next(["h2", "h3", "table"]):
            if node.name in ("h2", "h3"):
                if node is heading:
                    continue
                break
            if node.name == "table" and "wikitable" in (node.get("class") or []):
                formulas.extend(parse_formula_table(node, section))

    return formulas


def dedupe_rows(rows: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = key_fn(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def parse_file(path: Path) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "html.parser")
    effect_name, effect_type, reagents = parse_infobox(soup)
    descriptions = parse_descriptions(soup)
    potions, poisons = parse_effect_tables(soup)
    formulas = parse_formulas(soup)

    potions = dedupe_rows(potions, lambda r: (normalize(r["solvent"]), r["level"], normalize(r["name"])))
    poisons = dedupe_rows(poisons, lambda r: (normalize(r["solvent"]), r["level"], normalize(r["name"])))
    formulas = dedupe_rows(
        formulas,
        lambda r: (
            r["section"],
            tuple(normalize(x) for x in r["ingredients"]),
            tuple(normalize(x) for x in r["additional_effects"]),
        ),
    )

    return {
        "effect": effect_name,
        "effect_type": effect_type,
        "reagents": reagents,
        "descriptions": descriptions,
        "potions": potions,
        "poisons": poisons,
        "formulas": formulas,
        "source_file": path.name,
    }


def merge_effects(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    merged: dict[str, dict[str, Any]] = {}
    duplicate_files: list[str] = []

    for record in records:
        key = normalize(record["effect"])
        if not key:
            continue
        if key not in merged:
            merged[key] = record
            continue

        duplicate_files.append(record["source_file"])
        existing = merged[key]
        existing["reagents"] = sorted(set(existing["reagents"]) | set(record["reagents"]), key=normalize)
        if not existing["effect_type"]:
            existing["effect_type"] = record["effect_type"]
        for kind in ("potion", "poison"):
            if not existing["descriptions"][kind]:
                existing["descriptions"][kind] = record["descriptions"][kind]
        existing["potions"] = dedupe_rows(
            existing["potions"] + record["potions"],
            lambda r: (normalize(r["solvent"]), r["level"], normalize(r["name"])),
        )
        existing["poisons"] = dedupe_rows(
            existing["poisons"] + record["poisons"],
            lambda r: (normalize(r["solvent"]), r["level"], normalize(r["name"])),
        )
        existing["formulas"] = dedupe_rows(
            existing["formulas"] + record["formulas"],
            lambda r: (
                r["section"],
                tuple(normalize(x) for x in r["ingredients"]),
                tuple(normalize(x) for x in r["additional_effects"]),
            ),
        )
        if "source_files" not in existing:
            source_file = existing.pop("source_file", None)
            existing["source_files"] = []
            if source_file:
                existing["source_files"].append(source_file)
        existing["source_files"].append(record["source_file"])

    for record in merged.values():
        if "source_files" not in record:
            record["source_files"] = [record.pop("source_file")]

    return sorted(merged.values(), key=lambda r: normalize(r["effect"])), duplicate_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Import saved UESP ESO Alchemy effect pages into normalized JSON.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    files = sorted({*args.input.glob("*.htm"), *args.input.glob("*.html")})
    if not files:
        raise SystemExit(f"No .htm/.html files found in {args.input}")

    records = [parse_file(path) for path in files]
    effects, duplicate_files = merge_effects(records)

    output = {
        "source": "UESP",
        "source_kind": "saved_alchemy_effect_pages",
        "input_files": len(files),
        "unique_effects": len(effects),
        "duplicate_pages": duplicate_files,
        "effects": effects,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 64)
    print(" Black Feather Foundry - UESP Alchemy Importer")
    print("=" * 64)
    print(f"Input directory : {args.input}")
    print(f"HTML files      : {len(files)}")
    print(f"Unique effects  : {len(effects)}")
    print(f"Duplicate pages : {len(duplicate_files)}")
    print(f"Output          : {args.output}")
    print()
    for effect in effects:
        print(
            f"{effect['effect']}: "
            f"{len(effect['reagents'])} reagents, "
            f"{len(effect['potions'])} potion tiers, "
            f"{len(effect['poisons'])} poison tiers, "
            f"{len(effect['formulas'])} formulas"
        )


if __name__ == "__main__":
    main()
