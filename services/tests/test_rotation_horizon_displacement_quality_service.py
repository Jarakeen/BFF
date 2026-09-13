from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_horizon_displacement_quality_service import (
    RotationHorizonDisplacementQuality,
    RotationHorizonDisplacementQualityService,
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


def _plan(*, actions, unresolved) -> RotationPlan:
    return RotationPlan(
        character_name="Tester",
        build_name="DD",
        duration_seconds=60.0,
        actions=tuple(actions),
        unresolved=tuple(unresolved),
    )


def test_ordinary_slot_after_displacement_is_cadence_debt() -> None:
    plan = _plan(
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(30, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(45, 0, RotationActionKind.SKILL, name="Low", bar="front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    row = RotationHorizonDisplacementQualityService().classify(
        plan,
        priorities=_priorities(),
    ).rows[0]

    assert row.quality is RotationHorizonDisplacementQuality.ORDINARY_CADENCE_DEBT
    assert row.displaced_from_time_seconds == 30.0
    assert row.later_ordinary_skill_times == (45.0,)


def test_only_later_due_refreshes_are_protected_obligation_saturation() -> None:
    plan = _plan(
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(30, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
            RotationAction(45, 0, RotationActionKind.SKILL, name="Low", bar="front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "refresh obligation for 'Low' claimed the 45s front-bar slot from 'Mid'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    row = RotationHorizonDisplacementQualityService().classify(
        plan,
        priorities=_priorities(),
    ).rows[0]

    assert row.quality is RotationHorizonDisplacementQuality.PROTECTED_OBLIGATION_SATURATION
    assert row.later_same_bar_skill_times == (45.0,)
    assert row.later_ordinary_skill_times == ()


def test_no_later_same_bar_slot_is_late_window_truncation() -> None:
    plan = _plan(
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
            RotationAction(60, 0, RotationActionKind.SKILL, name="Mid", bar="front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 60s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    row = RotationHorizonDisplacementQualityService().classify(
        plan,
        priorities=_priorities(),
    ).rows[0]

    assert row.quality is RotationHorizonDisplacementQuality.LATE_WINDOW_TRUNCATION


def test_missing_displacement_start_fails_closed_as_unknown() -> None:
    plan = _plan(
        actions=(
            RotationAction(0, 0, RotationActionKind.SKILL, name="High", bar="front"),
        ),
        unresolved=(
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    report = RotationHorizonDisplacementQualityService().classify(
        plan,
        priorities=_priorities(),
    )
    row = report.rows[0]

    assert row.quality is RotationHorizonDisplacementQuality.UNKNOWN_PROVENANCE
    assert report.clean_of_proven_cadence_debt is True
