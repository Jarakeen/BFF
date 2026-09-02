from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_skill_coefficient_slots import load_slot_audit

DEFAULT_DATABASE = ROOT / "data" / "eso.db"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect every active skill coefficient with UESP type -73 before assigning Phase 6 semantics."
    )
    parser.add_argument("--database", default=str(DEFAULT_DATABASE))
    parser.add_argument("--samples", type=int, default=100)
    args = parser.parse_args()

    rows = tuple(row for row in load_slot_audit(args.database, limit=None) if row.coefficient_type == "-73")

    print("\n========================================")
    print(" PHASE 6 SPECIAL COEFFICIENT TYPE -73")
    print("========================================")
    print(f"Database: {args.database}")
    print(f"Rows:     {len(rows)}")

    for row in rows[: max(0, args.samples)]:
        print("\n----------------------------------------")
        print(
            f"rank={row.skill_rank_id} coef={row.coefficient_number} "
            f"ability={row.ability_id} name={row.name}"
        )
        print(
            f"type={row.coefficient_type} a={row.a} b={row.b} c={row.c} "
            f"r={row.r} avg={row.avg}"
        )
        print(
            f"raw_slot_type={row.raw_slot_type} raw_match={row.raw_slot_matches_coefficient} "
            f"placeholders={row.placeholder_numbers} own_placeholder={row.slot_placeholder_is_present}"
        )
        if row.coef_description:
            print("coef_description=" + " ".join(str(row.coef_description).split()))
        if row.raw_description:
            print("raw_description=" + " ".join(str(row.raw_description).split()))

    print("\nNOTE: diagnostic only. Type -73 is not assigned a mechanic by this tool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
