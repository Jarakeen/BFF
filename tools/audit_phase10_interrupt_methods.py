from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.encounter_interrupt_method_audit import audit_encounter_interrupt_methods
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.eso_combat_rules import STANDARD_INTERRUPT


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_interrupt_methods(service)

    print("PHASE 10 INTERRUPT METHOD AUDIT")
    print(f"Encounters with interrupt requirements: {audit.encounters_with_interrupt_requirements}")
    print(f"Encounters with resolved interrupt methods: {audit.encounters_with_resolved_methods}")
    print(f"Encounters missing interrupt-method detail: {audit.encounters_missing_method_detail}")
    print(f"Resolved interrupt methods: {audit.resolved_method_count}")
    print(f"Core-bash methods: {audit.core_bash_count}")
    print(f"Player-skill methods: {audit.player_skill_count}")
    print(f"Encounter-interaction methods: {audit.encounter_interaction_count}")
    print(f"Ranged-required methods: {audit.ranged_required_count}")
    print()
    print("UNRESOLVED INTERRUPT REQUIREMENTS")
    unresolved = [
        row
        for row in audit.rows
        if row.has_interrupt_requirement and not row.has_method_coverage
    ]
    if not unresolved:
        print("(none)")
    else:
        for row in unresolved:
            print(f"  {row.encounter_id}: requirements={row.interrupt_requirement_count}")

    print()
    print("GLOBAL RULE")
    print(f"{STANDARD_INTERRUPT.rule_id}: {STANDARD_INTERRUPT.statement}")
    print(f"Source: {STANDARD_INTERRUPT.source_name}")
    print()
    print("BOUNDARY")
    print("Encounter-specific interrupt evidence overrides the global core-bash rule.")
    print("Ranged interrupt is not required unless explicit encounter evidence says so.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
