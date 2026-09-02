from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_cleanse_method_audit import audit_encounter_cleanse_methods
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_cleanse_methods(service)

    print("PHASE 10 CLEANSE METHOD AUDIT")
    print(f"Encounters with cleanse requirements: {audit.encounters_with_cleanse_requirements}")
    print(f"Encounters with resolved cleanse methods: {audit.encounters_with_resolved_methods}")
    print(f"Encounters missing cleanse-method detail: {audit.encounters_missing_method_detail}")
    print(f"Resolved cleanse methods: {audit.resolved_method_count}")
    print(f"Encounter-interaction methods: {audit.encounter_interaction_count}")
    print(f"Core-action methods: {audit.core_action_count}")
    print(f"Player-build methods: {audit.player_build_method_count}")
    print()
    print("UNRESOLVED CLEANSE REQUIREMENTS")
    unresolved = [
        row
        for row in audit.rows
        if row.has_cleanse_requirement and not row.has_method_coverage
    ]
    if not unresolved:
        print("(none)")
    else:
        for row in unresolved:
            print(f"  {row.encounter_id}: requirements={row.cleanse_requirement_count}")

    print()
    print("BOUNDARY")
    print("A cleanse requirement is not treated as proof that a player cleanse skill works.")
    print("Player-skill effectiveness remains unknown unless explicit evidence establishes it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
