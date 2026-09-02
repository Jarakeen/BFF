from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from services.encounter_projection import load_encounter_definition


ROOT = Path(__file__).resolve().parents[2]
OAXILTSO = ROOT / "data" / "eso_info" / "bosses" / "oaxiltso.json"
EVIDENCE = ROOT / "data" / "encounter_evidence" / "rockgrove_boss1.json"


def _oaxiltso():
    return load_encounter_definition(OAXILTSO, evidence_packet_path=EVIDENCE)


def test_projects_source_identity_health_and_provenance_without_writing():
    encounter = _oaxiltso()

    assert encounter.encounter_id == "oaxiltso"
    assert encounter.content_id == "rockgrove"
    assert encounter.difficulty_health == (
        ("normal", "19,086,236"),
        ("veteran", "62,872,740"),
        ("hardmode", "125,745,480 (Hard Mode)"),
    )
    assert encounter.source.page_title == "Online:Oaxiltso"
    assert encounter.source.revision_id == "3304340"
    assert encounter.actors[0].kind == "boss"


def test_preserves_source_mechanics_and_explicit_cleanse_demand():
    encounter = _oaxiltso()
    sludge = next(mechanic for mechanic in encounter.mechanics if mechanic.name == "Noxious Sludge")

    assert sludge.interpretation_status == "inferred"
    assert sludge.target_count == 2
    assert sludge.requires_cleanse is True
    assert sludge.requires_positioning is True
    assert "prioritizing those farthest" in sludge.description


def test_conflicting_transition_remains_unresolved_with_all_evidence_retained():
    encounter = _oaxiltso()
    transition = next(
        fact
        for fact in encounter.evidence_facts
        if fact.fact_key == "havocrel_annihilator_spawn_thresholds"
    )

    assert transition.status == "conflicting"
    assert transition.value is None
    assert transition.distinct_sources == 2
    assert transition.distinct_values == 2
    assert len(transition.evidence) == 2


def test_projection_does_not_invent_phases_or_timers_from_source_prose():
    encounter = _oaxiltso()

    assert encounter.phases == ()
    assert not hasattr(encounter, "timeline")
    assert not hasattr(encounter, "positioning")
    assert not hasattr(encounter, "assignments")


def test_contract_is_immutable():
    encounter = _oaxiltso()

    with pytest.raises(FrozenInstanceError):
        encounter.name = "Not Oaxiltso"
