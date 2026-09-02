from pathlib import Path

from services.encounter_cleanse_method_audit import audit_encounter_cleanse_methods
from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService


ROOT = Path(__file__).resolve().parents[2]


def test_real_corpus_cleanse_method_audit_tracks_all_current_methods():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    audit = audit_encounter_cleanse_methods(service)

    assert audit.encounters_with_cleanse_requirements == 3
    assert audit.encounters_with_resolved_methods == 3
    assert audit.encounters_missing_method_detail == 0
    assert audit.resolved_method_count == 3
    assert audit.encounter_interaction_count == 2
    assert audit.core_action_count == 1
    assert audit.player_build_method_count == 0

    oaxiltso = next(row for row in audit.rows if row.encounter_id == "oaxiltso")
    assert oaxiltso.cleanse_requirement_count == 1
    assert oaxiltso.resolved_method_count == 1
    assert oaxiltso.encounter_interaction_count == 1

    hiath = next(row for row in audit.rows if row.encounter_id == "hiath_the_battlemaster")
    assert hiath.cleanse_requirement_count == 1
    assert hiath.resolved_method_count == 1
    assert hiath.core_action_count == 1

    xalvakka = next(row for row in audit.rows if row.encounter_id == "xalvakka")
    assert xalvakka.cleanse_requirement_count == 1
    assert xalvakka.resolved_method_count == 1
    assert xalvakka.encounter_interaction_count == 1
