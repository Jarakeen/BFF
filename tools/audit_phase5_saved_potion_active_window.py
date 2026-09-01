#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.build_model import BuildRoster
from minmax.potion_active_window import PotionActiveWindow
from minmax.potion_use_event import PotionUseEventResolver

BUILDS = ROOT / "data" / "builds.json"
CHECKPOINTS = (0.0, 12.0, 36.5, 36.6)


def main() -> int:
    print("========================================")
    print(" PHASE 5 SAVED POTION ACTIVE WINDOW AUDIT")
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
        if event.unresolved:
            failures += 1
            for message in event.unresolved:
                print(f"  Unresolved: {message}")
            print()
            continue

        for elapsed in CHECKPOINTS:
            window = PotionActiveWindow(event, elapsed_seconds=elapsed)
            names = ", ".join(window.active_buff_names) or "<none>"
            print(f"  t={elapsed:>4.1f}s -> {names}")
        print()

    print("Interpretation boundary:")
    print("  - Buffs appear only because this audit explicitly projects a potion-use event.")
    print("  - A grant expires when elapsed time reaches its ordinary sourced duration.")
    print("  - Cooldown and Medicinal Use are still not assumed.")
    print("  - Instant resource restores are not repeated by this active-window projection.")
    print("  - Database unchanged.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
