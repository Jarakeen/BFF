#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import BuildRoster
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver

BUILDS = ROOT / "data" / "builds.json"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}s"


def main() -> int:
    print("========================================")
    print(" PHASE 5 SAVED POTION CADENCE AUDIT")
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
        print(f"  Event resolved: {'yes' if event.resolved else 'NO'}")
        if not event.resolved:
            failures += 1
            for message in event.unresolved:
                print(f"    unresolved: {message}")
            print()
            continue

        for rank in (0, 3):
            cadence = PotionCadence(event, medicinal_use_rank=rank)
            print(
                f"  Medicinal Use rank {rank}: duration={_fmt(cadence.minimum_buff_duration)} | "
                f"cooldown={cadence.cooldown_seconds:.2f}s | gap={_fmt(cadence.guaranteed_gap_seconds)} | "
                f"overlap={_fmt(cadence.guaranteed_overlap_seconds)} | "
                f"continuous={'yes' if cadence.can_refresh_before_all_buffs_expire() else 'no'}"
            )
        print()

    print("Interpretation boundary:")
    print("  - Medicinal Use rank is shown as explicit scenarios, not inferred character ownership.")
    print("  - Base potion cooldown is 45 seconds; cooldown-reduction mechanics are not applied here.")
    print("  - Instant restores occur on use and are not treated as continuous effects.")
    print("  - Database unchanged.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
