from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from services.encounter_boss_guide import BossGuideTimelineFact
from services.encounter_evidence import EncounterEvidence, ReconciledEncounterFact
from services.rotation_tank_encounter_defensive_bundle_service import (
    RotationTankEncounterDefensiveBundleService,
)
from services.rotation_tank_encounter_defensive_timing_service import (
    RotationTankEncounterDefensiveTimingPolicy,
)


def _guide(*facts):
    return SimpleNamespace(encounter_id="test_boss", timeline_facts=tuple(facts))


def _timeline(*, key="heavy_time", start=10.0, end=10.8):
    return BossGuideTimelineFact(
        fact_id=1,
        canonical_kind="phase_transition",
        fact_type="timeline",
        fact_key=key,
        payload={"start_seconds": start, "end_seconds": end},
        review_status="reviewed",
        evidence_count=1,
    )


def _defensive_fact(*, key="heavy_response", value=None, status="single_source"):
    payload = value or {"target": "main_tank", "blockable": True}
    evidence = EncounterEvidence(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key=key,
        value=payload,
        source_type="guide",
        source_name="Reviewed Guide",
        source_locator="Heavy Attack",
        confidence="high",
    )
    return ReconciledEncounterFact(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key=key,
        status=status,
        value=None if status == "conflicting" else payload,
        evidence=(evidence,),
        distinct_sources=1,
        distinct_values=2 if status == "conflicting" else 1,
    )


def _policy(**overrides):
    values = dict(
        occurrence_id="heavy_01",
        timeline_fact_key="heavy_time",
        defensive_fact_type="mechanic_detail",
        defensive_fact_key="heavy_response",
        minimum_responses=1,
        bar="front",
    )
    values.update(overrides)
    return RotationTankEncounterDefensiveTimingPolicy(**values)


def test_projects_reviewed_clock_and_defensive_fact_into_exact_obligation():
    result = RotationTankEncounterDefensiveBundleService().project(
        guide=_guide(_timeline()),
        facts=(_defensive_fact(),),
        policies=(_policy(),),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert len(result.obligations) == 1
    obligation = result.obligations[0]
    assert obligation.window_start_seconds == 10.0
    assert obligation.window_end_seconds == 10.8
    assert obligation.allowed_actions == (RotationActionKind.BLOCK,)
    assert obligation.bar == "front"
    assert obligation.obligation_id.endswith(":heavy_01")


def test_repeated_occurrences_remain_distinct_and_sorted_by_clock():
    second = BossGuideTimelineFact(
        fact_id=2,
        canonical_kind="phase_transition",
        fact_type="timeline",
        fact_key="heavy_late",
        payload={"start_seconds": 30.0, "end_seconds": 30.5},
        review_status="reviewed",
        evidence_count=1,
    )
    result = RotationTankEncounterDefensiveBundleService().project(
        guide=_guide(_timeline(key="heavy_early", start=12.0, end=12.5), second),
        facts=(_defensive_fact(),),
        policies=(
            _policy(occurrence_id="late", timeline_fact_key="heavy_late"),
            _policy(occurrence_id="early", timeline_fact_key="heavy_early"),
        ),
    )

    assert result.unresolved == ()
    assert [row.window_start_seconds for row in result.obligations] == [12.0, 30.0]
    assert result.obligations[0].obligation_id.endswith(":early")
    assert result.obligations[1].obligation_id.endswith(":late")


def test_missing_reviewed_defensive_fact_fails_closed():
    result = RotationTankEncounterDefensiveBundleService().project(
        guide=_guide(_timeline()),
        facts=(),
        policies=(_policy(),),
    )

    assert result.obligations == ()
    assert result.resolved is False
    assert "reviewed defensive fact is missing" in result.unresolved[0]


def test_conflicting_defensive_fact_does_not_become_obligation():
    result = RotationTankEncounterDefensiveBundleService().project(
        guide=_guide(_timeline()),
        facts=(_defensive_fact(status="conflicting"),),
        policies=(_policy(),),
    )

    assert result.obligations == ()
    assert result.resolved is False
    assert "conflicting" in result.unresolved[0]


def test_unresolved_clock_timing_propagates_without_inventing_window():
    fact = BossGuideTimelineFact(
        fact_id=1,
        canonical_kind="phase_transition",
        fact_type="timeline",
        fact_key="heavy_time",
        payload={"threshold": "70%"},
        review_status="reviewed",
        evidence_count=1,
    )
    result = RotationTankEncounterDefensiveBundleService().project(
        guide=_guide(fact),
        facts=(_defensive_fact(),),
        policies=(_policy(),),
    )

    assert result.obligations == ()
    assert result.resolved is False
    assert "not converted to seconds" in result.unresolved[0]


def test_duplicate_reviewed_fact_identity_is_rejected():
    service = RotationTankEncounterDefensiveBundleService()
    try:
        service.project(
            guide=_guide(_timeline()),
            facts=(_defensive_fact(), _defensive_fact()),
            policies=(_policy(),),
        )
    except ValueError as exc:
        assert "duplicate reviewed defensive fact identity" in str(exc)
    else:
        raise AssertionError("Expected duplicate reviewed defensive fact identity to fail")
