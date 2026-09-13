from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_priority_displacement_audit_service import (
    RotationPriorityDisplacementAuditService,
)


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("front", 1, "High", 1),
            AbilityPriorityEntry("front", 2, "Mid", 5),
            AbilityPriorityEntry("front", 3, "Low", 10),
        ),
    )


def test_horizon_spillover_without_displacement_start_is_not_inversion() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Low", "front"),
        ),
        unresolved=(
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    result = RotationPriorityDisplacementAuditService().audit(
        plan,
        priorities=_priorities(),
    )

    assert result.priority_consistent
    assert result.inversions == ()
    assert result.displaced_beyond_horizon[0].displaced_from_time_seconds is None


def test_lower_priority_cast_before_displacement_is_not_inversion() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(10.0, 0, RotationActionKind.SKILL, "Low", "front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    result = RotationPriorityDisplacementAuditService().audit(
        plan,
        priorities=_priorities(),
    )

    assert result.priority_consistent
    assert result.inversions == ()
    assert result.displaced_beyond_horizon[0].displaced_from_time_seconds == 30.0


def test_lower_priority_cast_after_displacement_is_inversion() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(20.0, 0, RotationActionKind.SKILL, "Low", "front"),
            RotationAction(40.0, 0, RotationActionKind.SKILL, "Low", "front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    result = RotationPriorityDisplacementAuditService().audit(
        plan,
        priorities=_priorities(),
    )

    assert not result.priority_consistent
    assert len(result.inversions) == 1
    inversion = result.inversions[0]
    assert inversion.displaced_skill_name == "High"
    assert inversion.displaced_priority == 1
    assert inversion.displaced_from_time_seconds == 30.0
    assert inversion.lower_priority_skill_name == "Low"
    assert inversion.lower_priority == 10
    assert inversion.lower_priority_last_time_seconds == 40.0


def test_earliest_displacement_start_is_used_for_repeated_claims() -> None:
    plan = RotationPlan(
        character_name="Rylonia",
        build_name="Corpsebuster DD",
        duration_seconds=60.0,
        actions=(
            RotationAction(35.0, 0, RotationActionKind.SKILL, "Low", "front"),
        ),
        unresolved=(
            "refresh obligation for 'Mid' claimed the 30s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "refresh obligation for 'Mid' claimed the 45s front-bar slot from 'High'; displaced skill will cascade to the next same-bar skill slot",
            "skill 'High' was displaced beyond the 60s plan horizon after same-bar refresh/channel insertion on front bar",
        ),
    )

    result = RotationPriorityDisplacementAuditService().audit(
        plan,
        priorities=_priorities(),
    )

    assert len(result.inversions) == 1
    assert result.inversions[0].displaced_from_time_seconds == 30.0
