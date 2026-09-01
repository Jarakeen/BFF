from __future__ import annotations

from services.encounter_canonical_mapping import (
    CANONICAL_MECHANIC_PRESENCE,
    CANONICAL_PHASE_TRANSITION,
    CANONICAL_STATE,
    map_candidate_to_canonical,
)
from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence
from services.encounter_promotion import classify_encounter_fact_for_promotion


def _candidate(fact_type: str, fact_key: str, value):
    rows = [
        EncounterEvidence(
            encounter_id="taleria",
            fact_type=fact_type,
            fact_key=fact_key,
            value=value,
            source_type="uesp",
            source_name="UESP",
        ),
        EncounterEvidence(
            encounter_id="taleria",
            fact_type=fact_type,
            fact_key=fact_key,
            value=value,
            source_type="guide",
            source_name="Guide",
        ),
    ]
    fact = reconcile_encounter_evidence(rows)[0]
    return classify_encounter_fact_for_promotion(fact)


def test_maps_corroborated_mechanic_presence_without_claiming_lossless_schema():
    mapping = map_candidate_to_canonical(
        _candidate("mechanic_state", "rapid_deluge_exists", True)
    )

    assert mapping is not None
    assert mapping.canonical_kind == CANONICAL_MECHANIC_PRESENCE
    assert mapping.payload == {"name": "Rapid Deluge", "present": True}
    assert mapping.source_count == 2
    assert mapping.lossless_in_current_schema is False


def test_maps_corroborated_transition_thresholds():
    mapping = map_candidate_to_canonical(
        _candidate("transition", "bridge_thresholds", {"thresholds": ["50%", "35%", "20%"]})
    )

    assert mapping is not None
    assert mapping.canonical_kind == CANONICAL_PHASE_TRANSITION
    assert mapping.payload == {"thresholds": ["50%", "35%", "20%"]}
    assert mapping.lossless_in_current_schema is False


def test_maps_corroborated_encounter_state():
    mapping = map_candidate_to_canonical(
        _candidate("phase_state", "both_brothers_active", True)
    )

    assert mapping is not None
    assert mapping.canonical_kind == CANONICAL_STATE
    assert mapping.payload == {"key": "both_brothers_active", "value": True}


def test_single_source_candidate_is_not_mapped():
    row = EncounterEvidence(
        encounter_id="taleria",
        fact_type="mechanic_state",
        fact_key="winter_storm_exists",
        value=True,
        source_type="guide",
        source_name="Guide",
    )
    fact = reconcile_encounter_evidence([row])[0]
    candidate = classify_encounter_fact_for_promotion(fact)

    assert map_candidate_to_canonical(candidate) is None
