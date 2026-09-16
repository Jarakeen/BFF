from __future__ import annotations

"""Read-only E2 H1 ordinary five-piece gear denominator audit."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.config import DEFAULT_DATABASE
from services.extreme_actual_heal_gear_denominator_service import (
    ExtremeActualHealGearDenominatorService,
    ExtremeActualHealGearDisposition,
)


def main() -> int:
    report = ExtremeActualHealGearDenominatorService(DEFAULT_DATABASE).build()

    print("EXTREME E2 H1 ORDINARY GEAR DENOMINATOR AUDIT")
    print(f"database={DEFAULT_DATABASE}")
    print(f"canonical_set_count={report.denominator_count}")
    for disposition in ExtremeActualHealGearDisposition:
        print(f"{disposition.value}_count={report.count(disposition)}")
    print(f"disposition_total={report.disposition_total}")
    print(f"accepted_candidate_count={len(report.accepted_candidate_names)}")
    print(f"candidate_pool_matches_denominator={report.candidate_pool_matches_denominator}")
    print(f"ordinary_five_piece_denominator_proven={report.denominator_proven}")

    unresolved = tuple(
        row
        for row in report.rows
        if row.disposition is ExtremeActualHealGearDisposition.UNRESOLVED
    )
    print(f"unresolved_set_count={len(unresolved)}")
    for row in unresolved:
        print(
            f"UNRESOLVED set_id={row.set_id} set={row.set_name!r} category={row.category!r} "
            f"useful_piece_count={row.maximum_useful_piece_count} "
            f"objectives={row.unresolved_objectives!r}"
        )
        for blocker in row.blockers:
            print(f"  blocker={blocker!r}")

    print("DISPOSITION SAMPLE")
    for disposition in ExtremeActualHealGearDisposition:
        sample = tuple(
            row.set_name
            for row in report.rows
            if row.disposition is disposition
        )[:10]
        print(f"  {disposition.value}={sample!r}")

    if not report.denominator_proven:
        print("RESULT=FAIL: ordinary five-piece denominator is not internally reconciled")
        return 1

    print(
        "RESULT=PASS: every canonical set has one ordinary-H1 disposition and the "
        "accepted disposition exactly matches the authoritative candidate pool"
    )
    print(
        "NEXT_STEP=use unresolved_set_count and blocker evidence to close ordinary-set "
        "mechanic gaps; keep mythic/monster/arena/proc package families separate until "
        "their own denominators are reconciled"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
