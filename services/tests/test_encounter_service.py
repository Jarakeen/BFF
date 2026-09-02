from pathlib import Path

import pytest

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService

ROOT = Path(__file__).resolve().parents[2]


def test_oaxiltso_health_is_exactly_parsed_with_annotation_preserved():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    health = service.health("oaxiltso", "hardmode")
    assert health.raw_value == "125,745,480 (Hard Mode)"
    assert health.value == 125745480
    assert health.annotation == "Hard Mode"
    assert health.resolution == "parsed"


def test_unknown_health_stays_unresolved_without_coercion(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text('{"id":"x","health":{"normal":"about a lot"}}')
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))
    result = service.health("x", "normal")
    assert result.value is None and result.resolution == "unresolved"


def test_phase_threshold_parses_only_exact_single_percent(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","phases":['
        '{"label":"One","threshold":"75%","description":""},'
        '{"label":"Adds","threshold":"90%/75%/50%/25%","description":""}'
        ']}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    parsed = service.phase_threshold("x", "x:phase:1")
    unresolved = service.phase_threshold("x", "x:phase:2")

    assert (parsed.raw_value, parsed.percent, parsed.resolution) == ("75%", 75, "parsed")
    assert unresolved.raw_value == "90%/75%/50%/25%"
    assert unresolved.percent is None
    assert unresolved.resolution == "unresolved"


def test_phase_threshold_requires_exact_canonical_phase_id(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","phases":[{"label":"One","threshold":"75%","description":""}]}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    with pytest.raises(LookupError):
        service.phase_threshold("x", "One")


def test_oaxiltso_requirements_project_only_explicit_structured_demands():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    requirements = service.requirements("oaxiltso")

    sludge = tuple(row for row in requirements if row.mechanic_name == "Noxious Sludge")
    assert tuple(row.requirement_type for row in sludge) == (
        "movement",
        "positioning",
        "cleanse",
    )
    assert all(row.target_count == 2 for row in sludge)
    assert all(row.interpretation_status == "inferred" for row in sludge)

    blitz = tuple(row for row in requirements if row.mechanic_name == "Savage Blitz")
    assert tuple(row.requirement_type for row in blitz) == ("movement", "positioning")

    assert not any(row.requirement_type == "dodge" for row in requirements)
    assert not any(row.requirement_type == "interrupt" for row in requirements)


def test_requirements_do_not_promote_false_or_unknown_fields(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","mechanics":['
        '{"name":"Explicit","description":"should be interrupted and cleansed",'
        '"requires_movement":false,"requires_positioning":null,'
        '"requires_cleanse":true,"interruptible":null}'
        ']}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    requirements = service.requirements("x")

    assert len(requirements) == 1
    assert requirements[0].requirement_type == "cleanse"
    assert requirements[0].mechanic_name == "Explicit"
