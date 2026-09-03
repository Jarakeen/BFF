from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE, get_data_dir
from services.build_service import BuildService
from services.saved_build_capability_service import SavedBuildCapabilityService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print exact saved-build capability-resolution gaps for Phase 10 closeout."
    )
    parser.add_argument("--builds", type=Path, default=get_data_dir() / "builds.json")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    service = SavedBuildCapabilityService(BuildService(args.builds), args.database)
    audits = service.audit_roster()

    print("PHASE 10 SAVED-ROSTER CAPABILITY GAPS")
    print(f"Builds: {args.builds}")
    print(f"Database: {args.database}")
    print()

    blocked = 0
    for audit in audits:
        character = audit.character_name or "(unnamed character)"
        build = audit.build_name or "(unnamed build)"
        gaps = tuple(audit.capability_resolution_gaps)
        print(f"{character} | {build} | capability_gaps={len(gaps)}")
        if not gaps:
            print("  PASS no capability-resolution gaps")
        else:
            blocked += 1
            for gap in gaps:
                print(f"  - {gap}")
        print()

    print(f"BUILDS WITH CAPABILITY GAPS: {blocked}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
