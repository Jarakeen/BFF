from pathlib import Path

from services.encounter_execution_audit import audit_encounter_execution
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def test_real_corpus_execution_audit_tracks_ready_and_unknown_requirements():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_execution(service)

    assert audit.encounters_with_requirements > 0
    assert audit.covered_requirement_count > 0
    assert audit.unknown_requirement_count > 0

    achelir = next(row for row in audit.rows if row.encounter_id == "achelir")
    assert achelir.requirement_count == 1
    assert achelir.covered_count == 1
    assert achelir.unknown_count == 0
    assert achelir.fully_ready is True

    oaxiltso = next(row for row in audit.rows if row.encounter_id == "oaxiltso")
    assert oaxiltso.covered_count >= 1
    assert oaxiltso.unknown_count >= 1
    assert oaxiltso.fully_ready is False
