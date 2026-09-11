from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.encounter_runtime_observation_service import (
    EncounterRuntimeObservationService,
)


LOKKE_OBSERVATION = Path(
    "data/encounter_observations/sunspire_lokkestiiz_esologs_runtime.json"
)


def _payload() -> dict:
    return json.loads(LOKKE_OBSERVATION.read_text(encoding="utf-8"))


def test_loads_reviewed_lokkestiiz_runtime_strategy_observation() -> None:
    observation = EncounterRuntimeObservationService().load(LOKKE_OBSERVATION)

    assert observation.encounter_id == "lokkestiiz"
    assert observation.content_id == "sunspire"
    assert observation.observation_type == "runtime_strategy_evidence"
    assert observation.status == "reviewed"
    assert observation.source_type == "esologs_runtime_corpus"
    assert observation.successful_kills == 10
    assert observation.reviewed_window_count == 30
    assert observation.semantic_mechanic_key == "aerial_onslaught_flight"
    assert len(observation.source_reports) == 4

    conclusions = {row.key: row for row in observation.reviewed_conclusions}
    assert conclusions["flight_2_primary_sustained_pressure"].confidence == "repeated_observation"
    assert "9 of 10" in conclusions["flight_2_primary_sustained_pressure"].statement
    assert "4 of 10" in conclusions["flight_3_higher_death_incidence"].statement

    recurrence = observation.findings["within_kill_recurrence"]
    assert recurrence["highest_combined_incoming_pressure"] == {
        "flight_1": 0,
        "flight_2": 9,
        "flight_3": 1,
    }
    assert recurrence["highest_healer_output"] == {
        "flight_1": 0,
        "flight_2": 9,
        "flight_3": 1,
    }

    implications = {(row.role, row.priority): row.guidance for row in observation.strategy_implications}
    assert "Flight 2" in implications[("healer", "high")]
    assert any("canonical mechanics truth" in row for row in observation.limitations)


def test_runtime_observation_fails_closed_if_relabelled_as_canonical_mechanics() -> None:
    payload = _payload()
    payload["observation_type"] = "canonical_mechanic"

    with pytest.raises(ValueError, match="runtime strategy evidence"):
        EncounterRuntimeObservationService().from_payload(payload)


def test_runtime_observation_requires_repeated_observation_confidence() -> None:
    payload = _payload()
    payload = copy.deepcopy(payload)
    payload["reviewed_conclusions"][0]["confidence"] = "canonical"

    with pytest.raises(ValueError, match="Unsupported runtime observation confidence"):
        EncounterRuntimeObservationService().from_payload(payload)


def test_runtime_observation_requires_nonempty_limitations() -> None:
    payload = _payload()
    payload["limitations"] = []

    with pytest.raises(ValueError, match="requires limitations"):
        EncounterRuntimeObservationService().from_payload(payload)
