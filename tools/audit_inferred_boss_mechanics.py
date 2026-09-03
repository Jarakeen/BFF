from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics


def _default_source_dir() -> Path:
    candidates = (
        ROOT / "research" / "eso_info" / "bosses",
        ROOT / "data" / "eso_info" / "bosses",
    )
    for candidate in candidates:
        if any(candidate.glob("*.json")):
            return candidate
    return candidates[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit inferred boss mechanics awaiting human review.")
    parser.add_argument("--source-dir", type=Path, default=_default_source_dir())
    parser.add_argument("--samples", type=int, default=30)
    args = parser.parse_args()

    audit = audit_inferred_boss_mechanics(args.source_dir)

    print("=" * 72)
    print(" INFERRED BOSS MECHANIC REVIEW AUDIT")
    print("=" * 72)
    print(f"Source directory:              {args.source_dir}")
    print(f"Boss source files:             {audit.source_files}")
    print(f"Bosses with inferred mechanics:{audit.bosses_with_inferred_mechanics:>6}")
    print(f"Inferred mechanics:            {len(audit.rows):>6}")
    print(f"Rows with review issues:       {len(audit.issue_rows):>6}")
    print(f"Source parse failures:         {len(audit.failures):>6}")

    print("\nMECHANIC TYPES")
    for name, count in audit.mechanic_types.most_common():
        print(f"  {name:28} {count}")

    print("\nDAMAGE TYPES")
    for name, count in audit.damage_types.most_common():
        print(f"  {name:28} {count}")

    sample_count = max(0, args.samples)
    if audit.issue_rows:
        print("\nREVIEW ISSUES")
        for row in audit.issue_rows[:sample_count]:
            print(
                f"  - {row.encounter_id} :: {row.mechanic_name or '(unnamed)'} "
                f"[{', '.join(row.issues)}]"
            )
    else:
        print("\nNo structural defects were found in the inferred mechanic queue.")

    if audit.rows and sample_count:
        print("\nREVIEW QUEUE SAMPLE")
        for row in audit.rows[:sample_count]:
            flags = []
            if row.requires_movement is True:
                flags.append("movement")
            if row.requires_positioning is True:
                flags.append("positioning")
            if row.requires_cleanse is True:
                flags.append("cleanse")
            if row.persistent_hazard is True:
                flags.append("persistent")
            if row.failure_is_fatal is True:
                flags.append("fatal")
            if row.interruptible is True:
                flags.append("interrupt")
            flag_text = ",".join(flags) or "-"
            print(
                f"  - {row.encounter_id} :: {row.mechanic_name} | "
                f"type={row.mechanic_type or '?'} damage={row.damage_type or '?'} "
                f"targets={row.target_count if row.target_count is not None else '?'} flags={flag_text}"
            )

    if audit.failures:
        print("\nSOURCE FAILURES")
        for failure in audit.failures[:sample_count]:
            print(f"  - {failure}")

    print("\nRESULT: " + ("PASS" if not audit.failures and not audit.issue_rows else "REVIEW"))
    print("Read-only. No encounter mechanic or canonical fact rows were changed.")
    return 0 if not audit.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
