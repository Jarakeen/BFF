from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_timeline_projection_service import RotationTimelineProjectionService
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceRow,
)


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=30.0,
        actions=(
            RotationAction(0.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(1.0, 1, RotationActionKind.LIGHT_ATTACK, bar="front"),
            RotationAction(8.0, 2, RotationActionKind.SKILL, "Combat Prayer", "front"),
            RotationAction(10.0, 3, RotationActionKind.ULTIMATE, "Aggressive Horn", "back"),
            RotationAction(20.0, 4, RotationActionKind.SKILL, "Budding Seeds", "back"),
        ),
        unresolved=("one schedule gap",),
    )


def test_projection_keeps_only_skill_like_icon_actions_and_canonical_times():
    result = RotationTimelineProjectionService().project(_plan())

    assert [action.name for action in result.actions] == [
        "Combat Prayer",
        "Combat Prayer",
        "Aggressive Horn",
        "Budding Seeds",
    ]
    assert [action.time_seconds for action in result.actions] == [0.0, 8.0, 10.0, 20.0]
    assert result.actions[0].icon_key == "combat_prayer"
    assert result.lanes == ()
    assert result.unresolved == ("one schedule gap",)


def test_projection_uses_resolved_duration_evidence_and_merges_active_overlap():
    evidence = RotationDurationEvidence(
        rows=(
            RotationDurationEvidenceRow(
                ability="Combat Prayer",
                bar="Front",
                duration_seconds=10.0,
                casts=2,
                uptime_percent=60.0,
                gap_seconds=12.0,
                premature_seconds=2.0,
            ),
            RotationDurationEvidenceRow(
                ability="Budding Seeds",
                bar="Back",
                duration_seconds=12.0,
                casts=1,
                uptime_percent=33.3,
                gap_seconds=18.0,
                premature_seconds=0.0,
            ),
        ),
        summary="duration evidence",
        detail="resolved",
        unresolved=("one duration gap",),
    )

    result = RotationTimelineProjectionService().project(
        _plan(),
        duration_evidence=evidence,
    )

    assert [lane.lane_key for lane in result.lanes] == [
        "combat_prayer:front",
        "budding_seeds:back",
    ]
    combat_prayer = result.lanes[0]
    assert len(combat_prayer.segments) == 1
    assert combat_prayer.segments[0].start_seconds == 0.0
    assert combat_prayer.segments[0].end_seconds == 18.0

    budding_seeds = result.lanes[1]
    assert budding_seeds.segments[0].start_seconds == 20.0
    assert budding_seeds.segments[0].end_seconds == 30.0
    assert result.unresolved == ("one schedule gap", "one duration gap")


def test_projection_does_not_invent_duration_lane_when_bar_evidence_does_not_match():
    evidence = RotationDurationEvidence(
        rows=(
            RotationDurationEvidenceRow(
                ability="Combat Prayer",
                bar="Back",
                duration_seconds=10.0,
                casts=2,
                uptime_percent=0.0,
                gap_seconds=30.0,
                premature_seconds=0.0,
            ),
        ),
        summary="duration evidence",
        detail="bar mismatch",
        unresolved=(),
    )

    result = RotationTimelineProjectionService().project(
        _plan(),
        duration_evidence=evidence,
    )

    assert result.lanes == ()
