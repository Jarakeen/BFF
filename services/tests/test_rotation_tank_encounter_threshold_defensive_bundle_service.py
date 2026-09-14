from services.encounter_evidence import EncounterEvidence, ReconciledEncounterFact
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjection,
    EncounterThresholdClockPoint,
)
from services.rotation_tank_encounter_threshold_defensive_bundle_service import (
    RotationTankEncounterThresholdDefensiveBundleService,
)
from services.rotation_tank_encounter_threshold_defensive_timing_service import (
    RotationTankEncounterThresholdDefensiveTimingPolicy,
)
from minmax.rotation_plan import RotationActionKind


def _thresholds(*, time_seconds=20.0, unresolved=()):
    return EncounterHealthThresholdProjection(
        encounter_id="test_boss",
        difficulty="hardmode",
        maximum_health=100_000_000,
        trajectory=None,
        points=(
            EncounterThresholdClockPoint(
                fact_key="heavy_at_70",
                label="Heavy at 70%",
                threshold_fraction=0.70,
                time_seconds=time_seconds,
                resolved=time_seconds is not None,
                reason="" if time_seconds is not None else "threshold not reached",
            ),
        ),
        unresolved=tuple(unresolved),
    )


def _fact(*, value=None, status="single_source"):
    payload = value or {"target": "main_tank", "blockable": True}
    evidence = EncounterEvidence(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key="heavy_attack_response",
        value=payload,
        source_type="guide",
        source_name="Reviewed Guide",
        source_locator="Heavy Attack",
        confidence="high",
    )
    return ReconciledEncounterFact(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key="heavy_attack_response",
        status=status,
        value=None if status == "conflicting" else payload,
        evidence=(evidence,),
        distinct_sources=1,
        distinct_values=2 if status == "conflicting" else 1,
    )


def _policy(**overrides):
    values = {
        "occurrence_id": "heavy_70",
        "threshold_fact_key": "heavy_at_70",
        "threshold_fraction": 0.70,
        "defensive_fact_type": "mechanic_detail",
        "defensive_fact_key": "heavy_attack_response",
        "lead_seconds": 0.5,
        "window_seconds": 1.0,
        "minimum_responses": 1,
        "bar": "front",
    }
    values.update(overrides)
    return RotationTankEncounterThresholdDefensiveTimingPolicy(**values)


def test_projects_threshold_clock_and_reviewed_defensive_fact_into_obligation():
    result = RotationTankEncounterThresholdDefensiveBundleService().project(
        thresholds=_thresholds(),
        facts=(_fact(),),
        policies=(_policy(),),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.obligations) == 1
    obligation = result.obligations[0]
    assert obligation.allowed_actions == (RotationActionKind.BLOCK,)
    assert obligation.window_start_seconds == 19.5
    assert obligation.window_end_seconds == 21.0
    assert obligation.bar == "front"
    assert obligation.obligation_id.endswith(":heavy_70")


def test_wrong_threshold_fraction_fails_closed_without_inventing_clock_time():
    result = RotationTankEncounterThresholdDefensiveBundleService().project(
        thresholds=_thresholds(),
        facts=(_fact(),),
        policies=(_policy(threshold_fraction=0.65),),
    )

    assert result.obligations == ()
    assert result.unresolved
    assert "65%" in result.unresolved[0] or "0.65" in result.unresolved[0]


def test_missing_reviewed_defensive_fact_fails_closed():
    result = RotationTankEncounterThresholdDefensiveBundleService().project(
        thresholds=_thresholds(),
        facts=(),
        policies=(_policy(),),
    )

    assert result.obligations == ()
    assert result.unresolved == (
        "heavy_70: reviewed defensive fact is missing for mechanic_detail/heavy_attack_response",
    )


def test_conflicting_defensive_fact_does_not_become_obligation():
    result = RotationTankEncounterThresholdDefensiveBundleService().project(
        thresholds=_thresholds(),
        facts=(_fact(status="conflicting"),),
        policies=(_policy(),),
    )

    assert result.obligations == ()
    assert any("conflicting" in reason for reason in result.unresolved)


def test_duplicate_fact_identity_is_rejected():
    service = RotationTankEncounterThresholdDefensiveBundleService()
    try:
        service.project(
            thresholds=_thresholds(),
            facts=(_fact(), _fact()),
            policies=(_policy(),),
        )
    except ValueError as exc:
        assert "duplicate reviewed threshold defensive fact identity" in str(exc)
    else:
        raise AssertionError("Expected duplicate threshold defensive fact identity to fail")


def test_multiple_threshold_occurrences_sort_by_projected_time():
    thresholds = EncounterHealthThresholdProjection(
        encounter_id="test_boss",
        difficulty="hardmode",
        maximum_health=100_000_000,
        trajectory=None,
        points=(
            EncounterThresholdClockPoint(
                fact_key="late",
                label="Late",
                threshold_fraction=0.50,
                time_seconds=40.0,
                resolved=True,
                reason="",
            ),
            EncounterThresholdClockPoint(
                fact_key="early",
                label="Early",
                threshold_fraction=0.80,
                time_seconds=10.0,
                resolved=True,
                reason="",
            ),
        ),
        unresolved=(),
    )
    result = RotationTankEncounterThresholdDefensiveBundleService().project(
        thresholds=thresholds,
        facts=(_fact(),),
        policies=(
            _policy(
                occurrence_id="late",
                threshold_fact_key="late",
                threshold_fraction=0.50,
                lead_seconds=0.0,
            ),
            _policy(
                occurrence_id="early",
                threshold_fact_key="early",
                threshold_fraction=0.80,
                lead_seconds=0.0,
            ),
        ),
    )

    assert result.unresolved == ()
    assert [item.window_start_seconds for item in result.obligations] == [10.0, 40.0]
