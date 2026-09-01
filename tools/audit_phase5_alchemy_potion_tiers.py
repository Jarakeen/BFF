#!/usr/bin/env python3
"""Inspect recovered U50 Alchemy potion-tier evidence without changing data.

This is deliberately a source audit, not a mechanics parser. It prints the
normalized potion_tiers rows for potion effects used by production saved builds
so Phase 5 can implement temporal potion-use math from observed source values
rather than guesses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "alchemy_effects.json"
DEFAULT_EFFECTS = (
    "Restore Magicka",
    "Increase Spell Power",
    "Spell Critical",
    "Restore Health",
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").split())


def load_effects(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("effects", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Alchemy processed source does not contain an effects list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = clean(row.get("effect_name") or row.get("name"))
        if name:
            result[name.casefold()] = row
    return result


def potion_tier_rows(effect: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = effect.get("potion_tiers", [])
    if not isinstance(rows, list):
        return ()
    return tuple(row for row in rows if isinstance(row, dict))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit recovered U50 Alchemy potion tier values")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--effect", action="append", dest="effects")
    args = parser.parse_args()

    path = args.input.resolve()
    names = tuple(args.effects or DEFAULT_EFFECTS)

    print("========================================")
    print(" PHASE 5 ALCHEMY POTION TIER AUDIT")
    print("========================================")
    print(f"Processed source: {path}")
    print()

    if not path.exists():
        print("ERROR: processed Alchemy source does not exist.")
        return 1

    try:
        effects = load_effects(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    failures = 0
    for name in names:
        row = effects.get(name.casefold())
        print(name)
        if row is None:
            print("  NOT FOUND")
            print()
            failures += 1
            continue

        tiers = potion_tier_rows(row)
        print(f"  Potion tiers: {len(tiers)}")
        for index, tier in enumerate(tiers, start=1):
            solvent = clean(tier.get("solvent"))
            level = clean(tier.get("level"))
            potion_name = clean(tier.get("name"))
            values = tier.get("values", [])
            if not isinstance(values, list):
                values = [values]
            rendered_values = " | ".join(clean(value) for value in values if clean(value)) or "<none>"
            print(
                f"    {index:>2}. solvent={solvent!r} | level={level!r} | "
                f"name={potion_name!r} | values={rendered_values}"
            )
        print()

    print("Interpretation boundary:")
    print("  - Values above are raw normalized UESP table cells.")
    print("  - This audit does not infer magnitude, duration, cooldown, or Medicinal Use semantics.")
    print("  - Database unchanged.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
