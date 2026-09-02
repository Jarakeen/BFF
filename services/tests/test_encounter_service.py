from pathlib import Path
from services.encounter_service import EncounterService
from services.encounter_repository import EncounterRepository

ROOT = Path(__file__).resolve().parents[2]

def test_oaxiltso_health_is_exactly_parsed_with_annotation_preserved():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    health = service.health("oaxiltso", "hardmode")
    assert health.raw_value == "125,745,480 (Hard Mode)"
    assert health.value == 125745480
    assert health.annotation == "Hard Mode"
    assert health.resolution == "parsed"

def test_unknown_health_stays_unresolved_without_coercion(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"; evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True); evidence.mkdir()
    (boss / "x.json").write_text('{"id":"x","health":{"normal":"about a lot"}}')
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))
    result = service.health("x", "normal")
    assert result.value is None and result.resolution == "unresolved"
