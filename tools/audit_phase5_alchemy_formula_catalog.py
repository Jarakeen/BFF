#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minmax.alchemy_formula_catalog import AlchemyFormulaCatalog
from minmax.combat_effect_semantics import GameUpdate

DEFAULT_SOURCE = ROOT / "data" / "processed" / "alchemy_effects.json"


def _show_query(catalog: AlchemyFormulaCatalog, label: str, traits: tuple[str, ...], *, exact: bool) -> None:
    matches = catalog.find_by_traits(*traits, exact=exact)
    mode = "exact" if exact else "contains"
    print(f"  {label}: {len(matches)} ({mode}: {', '.join(traits)})")
    for formula in matches[:5]:
        print(f"    - {' + '.join(formula.reagents)}")
        print(f"      traits: {', '.join(formula.traits)}")
    if len(matches) > 5:
        print(f"    ... {len(matches) - 5} more")


def main() -> int:
    source = DEFAULT_SOURCE
    print("========================================")
    print(" PHASE 5 ALCHEMY FORMULA CATALOG AUDIT")
    print("========================================")
    print(f"Processed source: {source}")
    print()

    if not source.exists():
        print("Processed Alchemy source is missing.")
        return 1

    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read processed Alchemy source: {exc}")
        return 1

    effects = payload.get("effects", []) if isinstance(payload, dict) else []
    print(f"Processed effects: {len(effects) if isinstance(effects, list) else 0}")

    u50 = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U50)
    u51_legacy = AlchemyFormulaCatalog.from_processed_payload(
        payload,
        game_update=GameUpdate.U51,
        allow_legacy_alias=True,
    )
    u51_strict = AlchemyFormulaCatalog.from_processed_payload(payload, game_update=GameUpdate.U51)

    print(f"U50 canonical formulas:        {len(u50.formulas)}")
    print(f"U51 migrated legacy formulas: {len(u51_legacy.formulas)}")
    print(f"U51 strict source formulas:   {len(u51_strict.formulas)}")
    print(f"U50 unresolved rows:          {len(u50.unresolved)}")
    print(f"U51 strict unresolved rows:   {len(u51_strict.unresolved)}")
    print()

    trait_counts = Counter(trait for formula in u50.formulas for trait in formula.traits)
    print("Most common U50 formula traits:")
    for trait, count in trait_counts.most_common(15):
        print(f"  - {trait}: {count}")
    if not trait_counts:
        print("  (none)")
    print()

    print("Target family checks:")
    _show_query(
        u50,
        "Spell Power family",
        ("Restore Magicka", "Increase Spell Power", "Spell Critical"),
        exact=True,
    )
    _show_query(u50, "Spell Critical formulas", ("Spell Critical",), exact=False)
    _show_query(u50, "Timidity formulas", ("Timidity",), exact=False)
    _show_query(
        u51_legacy,
        "U51 migrated Magicka/Power/Critical family",
        ("Restore Magicka", "Increase Power", "Critical"),
        exact=True,
    )
    print()

    if u50.unresolved:
        print("Sample U50 unresolved formula evidence:")
        for message in u50.unresolved[:10]:
            print(f"  - {message}")
        if len(u50.unresolved) > 10:
            print(f"  ... {len(u50.unresolved) - 10} more")
        print()

    print("Interpretation boundary:")
    print("  - Formula rows come from explicit processed source evidence.")
    print("  - This audit does not infer unseen reagent compatibility rules.")
    print("  - U51 migrated view is for legacy-data migration, not historical source rewriting.")
    print("  - Database unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
