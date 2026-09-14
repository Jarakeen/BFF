from types import SimpleNamespace

from services.encounter_boss_guide import BossGuideTimelineFact
from services.rotation_tank_encounter_defensive_timing_service import (
    RotationTankEncounterDefensiveTimingPolicy,
    RotationTankEncounterDefensiveTimingService,
)


def _guide(*facts):
    return SimpleNamespace(
        encounter_id="test_boss",
        timeline_facts=tuple(facts),
    )


def _fact(*, key="heavy_01_time", payload=None, review_status="reviewed", evidence_count=1):
    return BossGuideTimelineFact(
        fact_id=1,
        canonical_kind="phase_transition",
        fact_type="timeline",
        fact_key=key,
        payload=payload or {},
        review_status=review_status,
        evidence_count=evidence_count,
    )


def _policy(**overrides):
    values = {
        "occurrence_id": "heavy_01",
        "timeline_fact_key": "heavy_01_time",
        "defensive_fact_type": "mechanic_detail",
        "defensive_fact_key": "heavy_attack_response",
        "minimum_responses": 1,
        "bar": "front",
    }
    values.update(overrides)
    return RotationTankEncounterDefensiveTimingPolicy(**values)


def test_binds_reviewed_explicit_clock_window_to_defensive_fact_identity() -> None:
    projection = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(
            _fact(payload={"start_seconds": 10.0, "end_seconds": 10.8})
        ),
        policies=(_policy(),),
    )

    assert projection.unresolved == ()
    assert projection.resolved is True
    assert len(projection.bindings) == 1
    binding = projection.bindings[0]
    assert binding.occurrence_id == "heavy_01"
    assert binding.fact_type == "mechanic_detail"
    assert binding.fact_key == "heavy_attack_response"
    assert binding.window_start_seconds == 10.0
    assert binding.window_end_seconds == 10.8
    assert binding.minimum_responses == 1
    assert binding.bar == "front"


def test_reuses_point_timing_width_and_lead_semantics_from_encounter_demand_service() -> None:
    projection = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(_fact(payload={"time_seconds": 20.0})),
        policies=(
            _policy(
                occurrence_id="heavy_02",
                lead_seconds=0.25,
                point_window_seconds=0.75,
                bar=None,
            ),
        ),
    )

    assert projection.resolved is True
    binding = projection.bindings[0]
    assert binding.window_start_seconds == 19.75
    assert binding.window_end_seconds == 20.75
    assert binding.bar is None


def test_health_or_phase_threshold_without_clock_evidence_fails_closed() -> None:
    projection = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(_fact(payload={"threshold": "70%"})),
        policies=(_policy(),),
    )

    assert projection.bindings == ()
    assert projection.unresolved == (
        "heavy_01: heavy_01_time: canonical encounter fact has no complete explicit clock window; health/phase thresholds are not converted to seconds",
    )


def test_unreviewed_or_unpersisted_timing_evidence_fails_closed() -> None:
    unreviewed = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(_fact(payload={"time_seconds": 10.0}, review_status="candidate")),
        policies=(_policy(point_window_seconds=0.5),),
    )
    assert unreviewed.bindings == ()
    assert "not reviewed" in unreviewed.unresolved[0]

    no_evidence = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(_fact(payload={"time_seconds": 10.0}, evidence_count=0)),
        policies=(_policy(point_window_seconds=0.5),),
    )
    assert no_evidence.bindings == ()
    assert "no persisted evidence rows" in no_evidence.unresolved[0]


def test_multiple_occurrences_sort_by_resolved_clock_time() -> None:
    projection = RotationTankEncounterDefensiveTimingService().project(
        guide=_guide(
            _fact(
                key="late_time",
                payload={"start_seconds": 30.0, "end_seconds": 31.0},
            ),
            BossGuideTimelineFact(
                fact_id=2,
                canonical_kind="phase_transition",
                fact_type="timeline",
                fact_key="early_time",
                payload={"start_seconds": 12.0, "end_seconds": 13.0},
                review_status="reviewed",
                evidence_count=1,
            ),
        ),
        policies=(
            _policy(
                occurrence_id="late",
                timeline_fact_key="late_time",
            ),
            _policy(
                occurrence_id="early",
                timeline_fact_key="early_time",
            ),
        ),
    )

    assert projection.unresolved == ()
    assert [binding.occurrence_id for binding in projection.bindings] == [
        "early",
        "late",
    ]


def test_duplicate_occurrence_ids_are_rejected() -> None:
    service = RotationTankEncounterDefensiveTimingService()
    try:
        service.project(
            guide=_guide(_fact(payload={"start_seconds": 10.0, "end_seconds": 11.0})),
            policies=(
                _policy(),
                _policy(),
            ),
        )
    except ValueError as exc:
        assert "duplicate tank defensive timing occurrence_id" in str(exc)
    else:
        raise AssertionError("Expected duplicate occurrence ids to be rejected")
