#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import BuildRoster
from minmax.potion_availability_repository import PotionAvailabilityRepository

BUILDS = ROOT / "data" / "builds.json"


def main() -> int:
    print("========================================")
    print(" PHASE 5 SAVED POTION AVAILABILITY AUDIT")
    print("========================================")
    print(f"Builds:   {BUILDS}")
    print()

    if not BUILDS.exists():
        print("Build file missing.")
        return 1

    roster = BuildRoster.from_dict(json.loads(BUILDS.read_text(encoding="utf-8")))
    selected = [member for member in roster.Members if str(member.Potion or "").strip()]
    if not selected:
        print("No saved builds have a potion selection.")
        return 0

    repository = PotionAvailabilityRepository()
    failures = 0
    for build in selected:
        result = repository.resolve(build.Potion)
        print(f"{build.Name or '<unnamed>'} | {build.BuildName or '<unnamed build>'}")
        print(f"  Saved potion: {build.Potion}")
        print(f"  Resolved:     {'yes' if result.resolved else 'NO'}")
        print(f"  Formulas:     {len(result.formulas)}")
        if result.canonical_traits:
            print("  Traits:       " + ", ".join(result.canonical_traits))
        if result.formulas:
            print("  Formula IDs:")
            for formula in result.formulas:
                print(f"    - {formula.canonical_id}")
        if result.effects:
            print("  EffectVariants:")
            for effect in result.effects:
                print(
                    f"    - {effect.name} | layer={effect.layer.value} | "
                    f"trigger={effect.trigger} | category={effect.category.value if effect.category else 'unknown'}"
                )
        if result.unresolved:
            failures += 1
            print("  Unresolved:")
            for message in result.unresolved:
                print(f"    - {message}")
        print()

    print("Interpretation boundary:")
    print("  - A saved potion proves availability, not active uptime.")
    print("  - Potion effects are not applied to standing/static character stats here.")
    print("  - Cooldown, Medicinal Use, duration, and potion-use timing remain temporal work.")
    print("  - Database unchanged.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
