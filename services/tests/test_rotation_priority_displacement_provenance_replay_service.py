from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from services.rotation_priority_displacement_provenance_replay_service import (
    RotationPriorityDisplacementProvenanceReplayService,
)


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Tester",
        build_name="DD",
        role="DD",
        entries=(
            AbilityPriorityEntry(bar="front", slot=1, skill_name="High", priority=1),
            AbilityPriorityEntry(bar="front", slot=2, skill_name="Mid", priority=2),
            AbilityPriorityEntry(bar="front", slot=3, skill_name="Low", priority=3),
        ),
    )


def _plan(actions) -> RotationPlan:
    return RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=12.0,
        actions=tuple(actions),
    )


def test_replay_recovers_original_source_instance_for_observed_queue_tail() -> None:
    seed = _plan(
        (
            RotationAction(0, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(1, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(11, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(12, 0, RotationActionKind.SKILL, name="Low", bar="front"),
        )
    )

    replay = RotationPriorityDisplacementProvenanceReplayService().replay(
        seed_plan=seed,
        rules=(RotationRecastRule(skill_name="Mid", duration_seconds=10.0, bar="front"),),
        priorities=_priorities(),
    )

    row = next(item for item in replay.spillovers if item.skill_name == "Low")
    assert row.resolved is True
    assert row.source_time_seconds == 12.0
    assert row.source_sequence == 0
    assert row.last_observed_queue_time_seconds == 12.0
    assert len(row.plausible_instances) == 1


def test_replay_recovers_tail_requeued_by_final_refresh_claim() -> None:
    seed = _plan(
        (
            RotationAction(0, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(11, 0, RotationActionKind.SKILL, name="Low", bar="front"),
        )
    )

    replay = RotationPriorityDisplacementProvenanceReplayService().replay(
        seed_plan=seed,
        rules=(RotationRecastRule(skill_name="Mid", duration_seconds=10.0, bar="front"),),
        priorities=_priorities(),
    )

    row = next(item for item in replay.spillovers if item.skill_name == "Low")
    assert row.resolved is True
    assert row.source_time_seconds == 11.0
    assert row.source_sequence == 0
    assert row.last_observed_queue_time_seconds == 11.0


def test_replay_fails_closed_when_multiple_same_skill_instances_survive() -> None:
    seed = _plan(
        (
            RotationAction(0, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(1, 0, RotationActionKind.SKILL, name="Low", bar="front"),
            RotationAction(11, 0, RotationActionKind.SKILL, name="Low", bar="front"),
            RotationAction(12, 0, RotationActionKind.SKILL, name="High", bar="front"),
        )
    )

    replay = RotationPriorityDisplacementProvenanceReplayService().replay(
        seed_plan=seed,
        rules=(RotationRecastRule(skill_name="Mid", duration_seconds=10.0, bar="front"),),
        priorities=_priorities(),
    )

    row = next(item for item in replay.spillovers if item.skill_name == "Low")
    assert row.resolved is False
    assert row.source_time_seconds is None
    assert len(row.plausible_instances) >= 2
    assert "deduplicated production horizon diagnostic" in row.unresolved[0]
