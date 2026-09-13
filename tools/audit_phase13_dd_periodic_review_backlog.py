from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_review_status_service import (
    RotationDDPeriodicReviewStatus,
    RotationDDPeriodicReviewStatusService,
)


def audit() -> int:
    dispositions = RotationDDPeriodicReviewStatusService().dispositions()
    print("=" * 76)
    print(" DD PERIODIC RUNTIME REVIEW BACKLOG")
    print("=" * 76)
    print(f"Reviewed components: {len(dispositions)}")
    print()

    complete = 0
    parked = 0
    partial = 0
    for item in dispositions:
        entry = item.entry
        unresolved = entry.unresolved_executable_fields
        if item.status is RotationDDPeriodicReviewStatus.COMPLETE:
            complete += 1
        elif item.status is RotationDDPeriodicReviewStatus.PARKED:
            parked += 1
        else:
            partial += 1

        status = item.status.value.upper()
        fields = "none" if not unresolved else ", ".join(unresolved)
        print(f"- {entry.skill_entity_id} coeff={entry.coefficient_number}: {status}")
        print(f"  unresolved: {fields}")
        if item.status is RotationDDPeriodicReviewStatus.PARKED:
            print(f"  park reason: {item.reason}")

    print()
    print(f"Executable-complete reviews: {complete}")
    print(f"Active partial reviews: {partial}")
    print(f"Parked reviews: {parked}")
    print(
        "Guardrail: PARTIAL means evidence work remains active; PARKED means the "
        "current evidence source has been exhausted or is non-discriminating. Neither "
        "status infers or promotes missing mechanics."
    )
    return 0


def main() -> int:
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
