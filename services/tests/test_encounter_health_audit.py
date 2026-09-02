from pathlib import Path
from services.encounter_health_audit import audit_encounter_health
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService

ROOT = Path(__file__).resolve().parents[2]

def test_audit_is_complete_stable_and_preserves_real_source_value():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_health(service)
    assert len(audit.rows) == len(service.encounter_ids()) * 3
    assert tuple((row.encounter_id, row.difficulty) for row in audit.rows) == tuple(
        (encounter_id, difficulty) for encounter_id in service.encounter_ids() for difficulty in ("normal", "veteran", "hardmode")
    )
    oax = next(row for row in audit.rows if (row.encounter_id, row.difficulty) == ("oaxiltso", "hardmode"))
    assert (oax.raw_value, oax.value, oax.annotation, oax.resolution) == ("125,745,480 (Hard Mode)", 125745480, "Hard Mode", "parsed")

def test_missing_values_are_reported_not_converted_to_zero():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_health(service)
    assert audit.missing_count > 0
    assert all(row.value is None for row in audit.rows if not row.raw_value)
