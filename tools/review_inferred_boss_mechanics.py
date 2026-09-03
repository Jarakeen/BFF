from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_decisions import (
    ACCEPTED,
    PENDING,
    REJECTED,
    audit_decisions,
    load_decisions,
    write_pending_decision_manifest,
)


def _default_source_dir() -> Path:
    candidates = (
        ROOT / "research" / "eso_info" / "bosses",
        ROOT / "data" / "eso_info" / "bosses",
    )
    for candidate in candidates:
        if any(candidate.glob("*.json")):
            return candidate
    return candidates[-1]


def _default_manifest() -> Path:
    return ROOT / "data" / "encounter_reviews" / "inferred_boss_mechanics.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or audit explicit review decisions for inferred boss mechanics."
    )
    parser.add_argument("--source-dir", type=Path, default=_default_source_dir())
    parser.add_argument("--manifest", type=Path, default=_default_manifest())
    parser.add_argument(
        "--initialize",
        action="store_true",
        help="Write a complete pending review manifest from the current inferred-mechanic queue.",
    )
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()

    if args.initialize:
        path = write_pending_decision_manifest(args.source_dir, args.manifest)
        print(f"Initialized review manifest: {path}")

    if not args.manifest.exists():
        print(f"Review manifest does not exist: {args.manifest}")
        print("Run again with --initialize to create a complete pending manifest.")
        return 1

    try:
        decisions = load_decisions(args.manifest)
    except (OSError, ValueError) as exc:
        print(f"Unable to load review manifest: {exc}")
        return 1

    audit = audit_decisions(args.source_dir, decisions)
    counts = {
        PENDING: sum(row.status == PENDING for row in decisions),
        ACCEPTED: sum(row.status == ACCEPTED for row in decisions),
        REJECTED: sum(row.status == REJECTED for row in decisions),
    }

    print("=" * 72)
    print(" INFERRED BOSS MECHANIC REVIEW DECISIONS")
    print("=" * 72)
    print(f"Source directory:             {args.source_dir}")
    print(f"Manifest:                     {args.manifest}")
    print(f"Expected mechanics:           {audit.expected_count}")
    print(f"Decision rows:                {len(decisions)}")
    print(f"Pending:                      {counts[PENDING]}")
    print(f"Accepted:                     {counts[ACCEPTED]}")
    print(f"Rejected:                     {counts[REJECTED]}")
    print(f"Missing decisions:            {len(audit.missing)}")
    print(f"Extra decisions:              {len(audit.extra)}")
    print(f"Duplicate keys:               {len(audit.duplicate_keys)}")
    print(f"Invalid statuses:             {len(audit.invalid_statuses)}")
    print(f"Accepted without rationale:   {len(audit.accepted_without_rationale)}")
    print(f"Rejected without rationale:   {len(audit.rejected_without_rationale)}")

    samples = max(0, args.samples)
    if audit.missing:
        print("\nMISSING")
        for encounter_id, mechanic_name in audit.missing[:samples]:
            print(f"  - {encounter_id} :: {mechanic_name}")
    if audit.extra:
        print("\nEXTRA")
        for encounter_id, mechanic_name in audit.extra[:samples]:
            print(f"  - {encounter_id} :: {mechanic_name}")
    if audit.invalid_statuses:
        print("\nINVALID STATUS")
        for encounter_id, mechanic_name, status in audit.invalid_statuses[:samples]:
            print(f"  - {encounter_id} :: {mechanic_name} => {status!r}")

    print("\nRESULT: " + ("BLOCKED" if audit.blocked else "PASS"))
    print("No encounter or canonical-fact rows were changed.")
    return 1 if audit.blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
