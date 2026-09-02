from __future__ import annotations

from pathlib import Path

from services.encounter_repository import EncounterRepository
from services.encounter_requirement_audit import audit_encounter_requirements
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def test_requirement_audit_is_stable_and_preserves_oaxiltso_structured_fields():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_requirements(service)

    assert audit.mechanic_count == len(audit.rows)
    assert tuple((row.encounter_id, row.mechanic_id) for row in audit.rows) == tuple(
        (encounter_id, mechanic.mechanic_id)
        for encounter_id in service.encounter_ids()
        for mechanic in service.get(encounter_id).mechanics
    )

    sludge = next(
        row
        for row in audit.rows
        if row.encounter_id == "oaxiltso" and row.mechanic_name == "Noxious Sludge"
    )
    assert sludge.movement is True
    assert sludge.positioning is True
    assert sludge.cleanse is True
    assert sludge.interruptible is None
    assert sludge.target_count == 2
    assert sludge.explicit_requirement_count == 3
    assert sludge.unresolved_requirement_field_count == 1


def test_requirement_audit_reports_unknowns_without_converting_them_to_false():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_requirements(service)

    assert audit.mechanics_with_requirements > 0
    assert audit.explicit_requirement_count > 0
    assert audit.mechanics_with_unresolved_requirement_fields > 0
    assert any(
        value is None
        for row in audit.rows
        for value in (row.movement, row.positioning, row.cleanse, row.interruptible)
    )
