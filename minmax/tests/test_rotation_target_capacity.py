import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_target_capacity import (
    RotationTargetCapacityAssessor,
    RotationTargetCapacityRequirement,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _demand(target_count: int = 12) -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Raid burst heal",
        start_seconds=10.0,
        end_seconds=15.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=target_count,
    )


def test_target_capacity_rejects_matching_cast_below_demand_count() -> None:
    assessment = RotationTargetCapacityAssessor().assess(
        _plan(
            RotationAction(
                12.0,
                0,
                RotationActionKind.SKILL,
                "Limited Heal",
                "front",
            )
        ),
        (_demand(12),),
        (
            RotationTargetCapacityRequirement(
                demand_name="Raid burst heal",
                action_name="Limited Heal",
                action_kind=RotationActionKind.SKILL,
                bar="front",
                maximum_targets=6,
            ),
        ),
    )

    assert assessment.legal is False
    assert len(assessment.violations) == 1
    violation = assessment.violations[0]
    assert violation.time_seconds == 12.0
    assert violation.shortfall == 6
    assert "cap 6" in violation.reason
    assert "count 12" in violation.reason


def test_target_capacity_accepts_exact_boundary_and_does_not_infer_geometry() -> None:
    assessment = RotationTargetCapacityAssessor().assess(
        _plan(
            RotationAction(
                12.0,
                0,
                RotationActionKind.SKILL,
                "Raid Heal",
                "front",
            )
        ),
        (_demand(12),),
        (
            RotationTargetCapacityRequirement(
                demand_name="Raid burst heal",
                action_name="Raid Heal",
                maximum_targets=12,
            ),
        ),
    )

    assert assessment.legal is True
    assert assessment.violations == ()


def test_target_capacity_only_applies_to_matching_action_inside_named_demand() -> None:
    assessment = RotationTargetCapacityAssessor().assess(
        _plan(
            RotationAction(
                9.0,
                0,
                RotationActionKind.SKILL,
                "Limited Heal",
                "front",
            ),
            RotationAction(
                12.0,
                0,
                RotationActionKind.SKILL,
                "Different Heal",
                "front",
            ),
        ),
        (_demand(12),),
        (
            RotationTargetCapacityRequirement(
                demand_name="Raid burst heal",
                action_name="Limited Heal",
                maximum_targets=1,
            ),
        ),
    )

    assert assessment.legal is True
    assert assessment.violations == ()


def test_target_capacity_requires_known_demand_and_unique_requirement() -> None:
    assessor = RotationTargetCapacityAssessor()
    requirement = RotationTargetCapacityRequirement(
        demand_name="Raid burst heal",
        action_name="Limited Heal",
        maximum_targets=6,
    )

    with pytest.raises(ValueError, match="unknown demand"):
        assessor.assess(_plan(), (), (requirement,))

    with pytest.raises(ValueError, match="duplicate rotation target capacity requirement"):
        assessor.assess(_plan(), (_demand(),), (requirement, requirement))
