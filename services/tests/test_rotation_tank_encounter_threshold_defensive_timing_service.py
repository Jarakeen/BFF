from __future__ import annotations

import pytest

from minmax.fight_damage_trajectory import RaidDamageSegment
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)
from services.rotation_tank_encounter_threshold_defensive_timing_service import (
    RotationTankEncounterThresholdDefensiveTimingPolicy,
    RotationTankEncounterThresholdDefensiveTimingService,
)


def _guide(*, thresholds=("70%",)) -> EncounterBossGuide:
    payload = (
        {"threshold": thresholds[0], "label": "Phase 2"}
        if len(thresholds) == 1
        else {"thresholds": list(thresholds), "label": "Transitions"}
    )
    return EncounterBossGuide(
        encounter_id="xalvakka",
        content_id="rockgrove",
        content_name="Rockgrove",
        name="Xalvakka",
        summary="",
        location="",
        species="",
        reaction="",
        health_record_present=True,
        health=(("hardmode", "100,000,000"),),
        abilities=(),
        phases=(),
        structural_phases=(),
        timeline_facts=(
            BossGuideTimelineFact(
                fact_id=1,
                canonical_kind="phase_transition",
                fact_type="phase",
                fact_key="phase_transitions",
                payload=payload,
                review_status="reviewed_corroborated",
                evidence_count=3,
            ),
        ),
        source_url="",
        source_page_title="",
        source_revision_id="",
        retrieved_at="",
        source_license="",
    )


def _thresholds(*, end_seconds: float | None = None, fractions=("70%",)):
    return EncounterHealthThresholdProjectionService().project(
        guide=_guide(thresholds=fractions),
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, end_seconds, 1_000_000.0),),
    )


def _policy(**overrides) -> RotationTankEncounterThresholdDefensiveTimingPolicy:
    values = {
        "occurrence_id": "phase_2_heavy",
        "threshold_fact_key": "phase_transitions",
        "threshold_fraction": 0.70,
        "defensive_fact_type": "mechanic_detail",
        "defensive_fact_key": "heavy_attack_response",
        "lead_seconds": 3.0,
        "window_seconds": 2.0,
        "minimum_responses": 1,
        "bar": "front",
    }
    values.update(overrides)
    return RotationTankEncounterThresholdDefensiveTimingPolicy(**values)


def test_binds_resolved_health_threshold_to_tank_defensive_window() -> None:
    result = RotationTankEncounterThresholdDefensiveTimingService().project(
        thresholds=_thresholds(),
        policies=(_policy(),),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.bindings) == 1
    binding = result.bindings[0]
    assert binding.occurrence_id == "phase_2_heavy"
    assert binding.fact_type == "mechanic_detail"
    assert binding.fact_key == "heavy_attack_response"
    assert binding.window_start_seconds == pytest.approx(27.0)
    assert binding.window_end_seconds == pytest.approx(32.0)
    assert binding.minimum_responses == 1
    assert binding.bar == "front"


def test_unresolved_damage_trajectory_stays_unresolved() -> None:
    result = RotationTankEncounterThresholdDefensiveTimingService().project(
        thresholds=_thresholds(end_seconds=20.0),
        policies=(_policy(),),
    )

    assert result.bindings == ()
    assert result.resolved is False
    assert len(result.unresolved) == 1
    assert "clock projection unresolved" in result.unresolved[0]


def test_missing_threshold_fraction_stays_unresolved() -> None:
    result = RotationTankEncounterThresholdDefensiveTimingService().project(
        thresholds=_thresholds(),
        policies=(_policy(threshold_fraction=0.40),),
    )

    assert result.bindings == ()
    assert "no projected canonical threshold point" in result.unresolved[0]


def test_distinct_threshold_occurrences_remain_distinct_and_sorted() -> None:
    result = RotationTankEncounterThresholdDefensiveTimingService().project(
        thresholds=_thresholds(fractions=("70%", "40%")),
        policies=(
            _policy(
                occurrence_id="phase_3_heavy",
                threshold_fraction=0.40,
                defensive_fact_key="phase_3_heavy_response",
            ),
            _policy(
                occurrence_id="phase_2_heavy",
                threshold_fraction=0.70,
                defensive_fact_key="phase_2_heavy_response",
            ),
        ),
    )

    assert result.unresolved == ()
    assert [binding.occurrence_id for binding in result.bindings] == [
        "phase_2_heavy",
        "phase_3_heavy",
    ]
    assert result.bindings[0].window_start_seconds == pytest.approx(27.0)
    assert result.bindings[1].window_start_seconds == pytest.approx(57.0)


def test_duplicate_occurrence_id_is_rejected() -> None:
    policy = _policy()
    with pytest.raises(ValueError, match="duplicate tank threshold defensive timing occurrence_id"):
        RotationTankEncounterThresholdDefensiveTimingService().project(
            thresholds=_thresholds(),
            policies=(policy, policy),
        )
