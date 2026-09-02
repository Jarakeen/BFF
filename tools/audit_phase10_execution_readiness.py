from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_execution_audit import audit_encounter_execution
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_execution(service)

    print("PHASE 10 EXECUTION READINESS AUDIT")
    print(f"Encounters with structured requirements: {audit.encounters_with_requirements}")
    print(f"Fully evaluable encounters: {audit.fully_evaluable_encounters}")
    print(f"Fully build-independent ready encounters: {audit.fully_ready_encounters}")
    print(f"Covered build-independent requirements: {audit.covered_requirement_count}")
    print(f"Unknown execution requirements: {audit.unknown_requirement_count}")
    print(f"Conflicting execution requirements: {audit.conflict_requirement_count}")
    print()
    print("UNRESOLVED EXECUTION REQUIREMENTS")
    unresolved = [row for row in audit.rows if row.has_requirements and row.unknown_count]
    if not unresolved:
        print("(none)")
    else:
        for row in unresolved:
            print(
                f"  {row.encounter_id}: requirements={row.requirement_count} "
                f"covered={row.covered_count} unknown={row.unknown_count}"
            )
    print()
    print("BOUNDARY")
    print("Covered means the required handling capability is available without a special build.")
    print("It does not claim the roster will execute movement, positioning, bash, or interactions correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
