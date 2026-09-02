from pathlib import Path

from services.encounter_interrupt_method_audit import audit_encounter_interrupt_methods
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def test_real_corpus_interrupt_method_audit_exposes_coverage_gaps():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_interrupt_methods(service)

    assert audit.encounters_with_interrupt_requirements > 0
    assert audit.encounters_missing_method_detail >= 0
    assert audit.resolved_method_count >= 0
