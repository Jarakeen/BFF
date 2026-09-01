#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import BuildRoster
from minmax.potion_use_event import PotionUseEventResolver

BUILDS = ROOT / "data" / "builds.json"


def main() -> int:
    print("========================================")
    print(" PHASE 5 SAVED POTION USE EVENT AUDIT")
    print("========================================")
    print(f"Builds: {BUILDS}")
    print()

    if not BUILDS.exists():
        print("ERROR: builds.json not found")
        return 1

    roster = BuildRoster.from_dict(json.loads(BUILDS.read_text(encoding="utf-8")))
    resolver = PotionUseEventResolver()
    failures = 0

    for build in roster.Members:
        potion = str(build.Potion or "").strip()
        if not potion:
            continue
        event = resolver.resolve(potion)
        print(f"{build.Name or '<unnamed>'} | {build.BuildName or '<unnamed build>'}")
        print(f"  Saved potion: {potion}")
        print(f"  Resolved:     {'yes' if event.resolved else 'NO'}")
        print(f"  Formula IDs:  {len(event.formula_ids)}")
        if event.instant_restores:
            print("  Instant restores:")
            for value in event.instant_restores:
                print(
                    f"    - {value.trait} | magnitude={value.magnitude:g} | "
                    f"tier={value.tier_name} | solvent={value.solvent}"
                )
        if event.timed_traits:
            print("  Timed traits:")
            for value in event.timed_traits:
                print(
                    f"    - {value.trait} | duration={value.duration:g}s | "
                    f"triple_candidate={value.triple_duration:g}s | tier={value.tier_name}"
                )
        if event.buff_grants:
            print("  Named buff grants:")
            for grant in event.buff_grants:
                print(
                    f"    - {grant.source_trait} -> {grant.buff_name} | "
                    f"duration={grant.duration:g}s | "
                    f"triple_candidate={grant.triple_duration:g}s | tier={grant.tier_name}"
                )
        if event.unresolved:
            failures += 1
            print("  Unresolved:")
            for message in event.unresolved:
                print(f"    - {message}")
        print()

    print("Interpretation boundary:")
    print("  - This represents an explicit potion-use event, not standing uptime.")
    print("  - Instant restores are events; they are not timed buffs.")
    print("  - Named buff grants are source-backed temporal effects and are not auto-applied to CombatState.")
    print("  - Ordinary source duration is used by default.")
    print("  - Triple-duration values remain evidence only until three-reagent trait support is proven.")
    print("  - Medicinal Use and potion cooldown are not applied here.")
    print("  - Database unchanged.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
