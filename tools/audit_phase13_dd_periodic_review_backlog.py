from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


_PARKED: dict[tuple[str, int], str] = {
    ("unnerving_boneyard", 1): (
        "current corpus cannot resolve exact first-tick offset or magnitude policy"
    ),
    ("detonating_siphon", 1): (
        "production geometry/timing remains fail-closed pending controlled spatial evidence"
    ),
    ("skeletal_archer", 1): (
        "current corpus exposes no explicit pet-to-owner linkage for candidate 122774"
    ),
    ("scalding_rune", 2): (
        "current corpus has no stable-state magnitude controls"
    ),
    ("meteor", 2): (
        "current corpus has no identifiable Meteor-family cast/damage evidence"
    ),
}


def audit() -> int:
    entries = RotationDDPeriodicRuntimeSemanticsReviewService().load()
    print("=" * 76)
    print(" DD PERIODIC RUNTIME REVIEW BACKLOG")
    print("=" * 76)
    print(f"Reviewed components: {len(entries)}")
    print()

    complete = 0
    parked = 0
    partial = 0
    for entry in entries:
        unresolved = entry.unresolved_executable_fields
        key = (entry.skill_entity_id, entry.coefficient_number)
        if not unresolved:
            complete += 1
            status = "COMPLETE"
        elif key in _PARKED:
            parked += 1
            status = "PARKED"
        else:
            partial += 1
            status = "PARTIAL"

        fields = "none" if not unresolved else ", ".join(unresolved)
        print(
            f"- {entry.skill_entity_id} coeff={entry.coefficient_number}: {status}"
        )
        print(f"  unresolved: {fields}")
        if status == "PARKED":
            print(f"  park reason: {_PARKED[key]}")

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
