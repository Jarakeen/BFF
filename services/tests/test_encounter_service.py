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


def test_oaxiltso_target_constraints_preserve_explicit_count_without_selecting_targets():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    constraints = service.target_constraints("oaxiltso")

    sludge = next(row for row in constraints if row.mechanic_name == "Noxious Sludge")
    assert sludge.target_count == 2
    assert sludge.constraint_id == f"{sludge.mechanic_id}:targets"
    assert sludge.interpretation_status == "inferred"
    assert not hasattr(sludge, "selected_targets")
    assert not hasattr(sludge, "targeting_rule")


def test_target_constraints_ignore_missing_nonpositive_and_boolean_counts(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text(
        '{"id":"x","mechanics":['
        '{"name":"Missing","description":"","target_count":null},'
        '{"name":"Zero","description":"","target_count":0},'
        '{"name":"Boolean","description":"","target_count":true},'
        '{"name":"Exact","description":"","target_count":3}'
        ']}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    constraints = service.target_constraints("x")

    assert len(constraints) == 1
    assert constraints[0].mechanic_name == "Exact"
    assert constraints[0].target_count == 3


def test_evidence_facts_filter_by_exact_fact_type():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))

    transitions = service.evidence_facts("tideborn_taleria", "transition")

    assert transitions
    assert all(fact.fact_type == "transition" for fact in transitions)
    assert any(fact.fact_key == "bridge_thresholds" for fact in transitions)
    assert service.evidence_facts("tideborn_taleria", "Transition") == ()
    with pytest.raises(ValueError):
        service.evidence_facts("tideborn_taleria", "")


def test_taleria_temporal_evidence_preserves_keys_approximation_and_source_status():
    service = EncounterService(EncounterRepository.from_data_root(ROOT / "data"))
    temporal = service.temporal_evidence("tideborn_taleria")
    by_ref = {(row.fact_key, row.value_key): row for row in temporal}

    duration = by_ref[("maelstrom_veteran_behavior", "duration_seconds")]
    assert duration.seconds == 6
    assert duration.approximate is False
    assert duration.reconciliation_status == "single_source"
    assert duration.distinct_sources == 1

    cooldown = by_ref[("maelstrom_veteran_behavior", "cooldown_seconds")]
    assert cooldown.seconds == 20
    assert cooldown.approximate is False

    detonation = by_ref[("rapid_deluge_veteran_behavior", "detonation_seconds_approx")]
    assert detonation.seconds == 6
    assert detonation.approximate is True

    interval_min = by_ref[("behemoth_spawn_interval", "seconds_approx_min")]
    interval_max = by_ref[("behemoth_spawn_interval", "seconds_approx_max")]
    assert (interval_min.seconds, interval_max.seconds) == (60, 70)
    assert interval_min.approximate is True
    assert interval_max.approximate is True


def test_conflicting_temporal_fact_is_not_converted_to_a_timer(tmp_path):
    boss = tmp_path / "eso_info" / "bosses"
    evidence = tmp_path / "encounter_evidence"
    boss.mkdir(parents=True)
    evidence.mkdir()
    (boss / "x.json").write_text('{"id":"x"}')
    (evidence / "x.json").write_text(
        '{"encounter_id":"x","evidence":['
        '{"fact_type":"mechanic_detail","fact_key":"timer",'
        '"value":{"duration_seconds":10},"source_type":"guide",'
        '"source_name":"A"},'
        '{"fact_type":"mechanic_detail","fact_key":"timer",'
        '"value":{"duration_seconds":12},"source_type":"guide",'
        '"source_name":"B"}'
        ']}'
    )
    service = EncounterService(EncounterRepository.from_data_root(tmp_path))

    fact = service.evidence_facts("x", "mechanic_detail")[0]
    assert fact.status == "conflicting"
    assert fact.value is None
    assert service.temporal_evidence("x") == ()
