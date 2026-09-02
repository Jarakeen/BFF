from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_model_audit import audit_encounter_model
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(REPO_ROOT / "data"))
    audit = audit_encounter_model(service)

    print("PHASE 9 ENCOUNTER MODEL AUDIT")
    print(f"Encounters: {audit.encounter_count}")
    print(f"With mechanics: {audit.encounters_with_mechanics}")
    print(f"With phases: {audit.encounters_with_phases}")
    print(f"With requirements: {audit.encounters_with_requirements}")
    print(f"With positioning constraints: {audit.encounters_with_positioning_constraints}")
    print(f"With temporal evidence: {audit.encounters_with_temporal_evidence}")
    print(f"With transition evidence: {audit.encounters_with_transition_evidence}")
    print(f"With target constraints: {audit.encounters_with_target_constraints}")
    print(f"With reconciled evidence: {audit.encounters_with_evidence}")
    print(f"With explicit add-group evidence: {audit.encounters_with_add_group_evidence}")
    print(f"With explicit damage-window evidence: {audit.encounters_with_damage_window_evidence}")
    print()
    print("BOUNDARIES")
    print("Add groups require exact add_group evidence; summon prose is not promoted.")
    print("Damage windows require exact damage_window evidence; invulnerability prose is not promoted.")
    print("Positioning records requirements only; manual board coordinates are not canonical truth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
