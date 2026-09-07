from __future__ import annotations

from types import SimpleNamespace

from minmax.rotation_demand_window import RotationDemandKind, RotationDemandPattern
from services.encounter_boss_guide import BossGuideTimelineFact
from services.encounter_rotation_demand_service import (
    EncounterRotationDemandPolicy,
    EncounterRotationDemandService,
)


def _guide(*facts: BossGuideTimelineFact):
    return SimpleNamespace(encounter_id="sunspire:nahviintaas", timeline_facts=tuple(facts))


def _fact(*, key: str, payload: dict, status: str = "reviewed_corroborated", evidence: int = 2):
    return BossGuideTimelineFact(
        fact_id=1,
        canonical_kind="phase_transition",
        fact_type="transition",
        fact_key=key,
        payload=payload,
        review_status=status,
        evidence_count=evidence,
    )


def test_projects_explicit_start_end_seconds_with_role_policy() -> None:
    projection = EncounterRotationDemandService().project(
        guide=_guide(
            _fact(
                key="ice_cage_window",
                payload={
                    "label": "Ice Cage",
                    "start_seconds": 24.0,
                    "end_seconds": 30.0,
                },
            )
        ),
        policies=(
            EncounterRotationDemandPolicy(
                fact_key="ice_cage_window",
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
                lead_seconds=2.0,
                target_count=2,
            ),
        ),
    )

    assert projection.unresolved == ()
    assert len(projection.demands) == 1
    demand = projection.demands[0]
    assert demand.name == "Ice Cage"
    assert demand.start_seconds == 22.0
    assert demand.end_seconds == 30.0
    assert demand.kind is RotationDemandKind.HEALING
    assert demand.pattern is RotationDemandPattern.BURST
    assert demand.target_count == 2


def test_projects_point_time_only_when_policy_supplies_window_width() -> None:
    projection = EncounterRotationDemandService().project(
        guide=_guide(
            _fact(
                key="burst_hit",
                payload={"name": "Burst Hit", "time_seconds": 42.0},
            )
        ),
        policies=(
            EncounterRotationDemandPolicy(
                fact_key="burst_hit",
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
                lead_seconds=3.0,
                point_window_seconds=2.0,
            ),
        ),
    )

    demand = projection.demands[0]
    assert demand.start_seconds == 39.0
    assert demand.end_seconds == 44.0


def test_health_threshold_timeline_fact_is_not_fabricated_into_seconds() -> None:
    projection = EncounterRotationDemandService().project(
        guide=_guide(
            _fact(
                key="retreat_thresholds",
                payload={"thresholds": ["70%", "40%"], "event": "retreat"},
            )
        ),
        policies=(
            EncounterRotationDemandPolicy(
                fact_key="retreat_thresholds",
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
            ),
        ),
    )

    assert projection.demands == ()
    assert len(projection.unresolved) == 1
    assert "health/phase thresholds are not converted to seconds" in projection.unresolved[0]


def test_unreviewed_or_unproven_timeline_fact_does_not_schedule() -> None:
    service = EncounterRotationDemandService()
    policy = EncounterRotationDemandPolicy(
        fact_key="burst_hit",
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        point_window_seconds=2.0,
    )

    unreviewed = service.project(
        guide=_guide(
            _fact(
                key="burst_hit",
                payload={"time_seconds": 42.0},
                status="review_required",
            )
        ),
        policies=(policy,),
    )
    assert unreviewed.demands == ()
    assert "not reviewed" in unreviewed.unresolved[0]

    no_evidence = service.project(
        guide=_guide(
            _fact(
                key="burst_hit",
                payload={"time_seconds": 42.0},
                evidence=0,
            )
        ),
        policies=(policy,),
    )
    assert no_evidence.demands == ()
    assert "no persisted evidence rows" in no_evidence.unresolved[0]
