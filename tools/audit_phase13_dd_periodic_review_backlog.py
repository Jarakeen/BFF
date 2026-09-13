from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rotation_dd_periodic_runtime_semantics_review_service import (
    RotationDDPeriodicRuntimeSemanticsReviewService,
)


def audit() -> int:
    entries = RotationDDPeriodicRuntimeSemanticsReviewService().load()
    print("=" * 76)
    print(" DD PERIODIC RUNTIME REVIEW BACKLOG")
    print("=" * 76)
    print(f"Reviewed components: {len(entries)}")
    print()

    complete = 0
    for entry in entries:
        unresolved = entry.unresolved_executable_fields
        if not unresolved:
            complete += 1
        status = "COMPLETE" if not unresolved else "PARTIAL"
        fields = "none" if not unresolved else ", ".join(unresolved)
        print(
            f"- {entry.skill_entity_id} coeff={entry.coefficient_number}: {status}"
        )
        print(f"  unresolved: {fields}")

    print()
    print(f"Executable-complete reviews: {complete}")
    print(f"Partial reviews: {len(entries) - complete}")
    print(
        "Guardrail: PARTIAL means reviewed evidence is intentionally incomplete; "
        "this audit does not infer or promote missing mechanics."
    )
    return 0


def main() -> int:
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
