from __future__ import annotations

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import BossGuideTimelineFact, EncounterBossGuide
from services.encounter_health_threshold_projection_service import (
    EncounterHealthThresholdProjectionService,
)
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
    EncounterThresholdRotationDemandService,
)


def _guide() -> EncounterBossGuide:
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
                canonical_kind="phase",
                fact_type="phase",
                fact_key="phase_2",
                payload={"threshold": "70%", "label": "Phase 2"},
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


def _thresholds(*, end_seconds: float | None = None):
    return EncounterHealthThresholdProjectionService().project(
        guide=_guide(),
        difficulty="hardmode",
        damage_segments=(RaidDamageSegment(0.0, end_seconds, 1_000_000.0),),
    )


def _policy() -> EncounterThresholdRotationDemandPolicy:
    return EncounterThresholdRotationDemandPolicy(
        fact_key="phase_2",
        threshold_fraction=0.70,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        lead_seconds=3.0,
        window_seconds=2.0,
        target_count=12,
        name="Phase 2 healing prep",
    )


def test_projects_threshold_clock_point_into_role_demand_window() -> None:
    result = EncounterThresholdRotationDemandService().project(
        thresholds=_thresholds(),
        policies=(_policy(),),
    )

    assert result.unresolved == ()
    assert len(result.demands) == 1
    demand = result.demands[0]
    assert demand.name == "Phase 2 healing prep"
    assert demand.start_seconds == 27.0
    assert demand.end_seconds == 32.0
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.pattern is RotationDemandPattern.BURST
    assert demand.target_count == 12


def test_unresolved_threshold_clock_point_stays_unresolved() -> None:
    result = EncounterThresholdRotationDemandService().project(
        thresholds=_thresholds(end_seconds=20.0),
        policies=(_policy(),),
    )

    assert result.demands == ()
    assert len(result.unresolved) == 1
    assert "clock projection unresolved" in result.unresolved[0]


def test_missing_threshold_policy_target_stays_unresolved() -> None:
    missing = EncounterThresholdRotationDemandPolicy(
        fact_key="phase_2",
        threshold_fraction=0.40,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    result = EncounterThresholdRotationDemandService().project(
        thresholds=_thresholds(),
        policies=(missing,),
    )

    assert result.demands == ()
    assert "no projected canonical threshold point" in result.unresolved[0]


def test_duplicate_threshold_policy_is_rejected() -> None:
    policy = _policy()
    try:
        EncounterThresholdRotationDemandService().project(
            thresholds=_thresholds(),
            policies=(policy, policy),
        )
    except ValueError as exc:
        assert "duplicate threshold rotation demand policy" in str(exc)
    else:
        raise AssertionError("duplicate threshold policy should fail")
