from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_ultimate_affordability import (
    RotationUltimateAffordabilityAssessor,
    RotationUltimateAffordabilityRequirement,
)
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=actions,
    )


def test_shared_ultimate_pool_rejects_second_unaffordable_cast() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Barrier", bar="front"),
        RotationAction(20.0, 0, RotationActionKind.ULTIMATE, "Aggressive Horn", bar="back"),
    )
    requirement = RotationUltimateAffordabilityRequirement(
        starting_amount=300.0,
        spend_rules=(
            UltimateSpendRule("Barrier", 250.0),
            UltimateSpendRule("Aggressive Horn", 250.0),
        ),
    )

    assessment = RotationUltimateAffordabilityAssessor().assess(plan, requirement)

    assert len(assessment.violations) == 1
    violation = assessment.violations[0]
    assert violation.action_name == "Aggressive Horn"
    assert violation.time_seconds == 20.0
    assert violation.balance_before == 50.0
    assert violation.required_cost == 250.0
    assert violation.shortfall == 200.0
    assert assessment.ending_amount == 50.0


def test_same_time_generation_is_available_before_ultimate_spend() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Barrier", bar="front"),
    )
    requirement = RotationUltimateAffordabilityRequirement(
        starting_amount=200.0,
        spend_rules=(UltimateSpendRule("Barrier", 250.0),),
        generation_events=(
            UltimateGenerationEvent(10.0, 50.0, "verified generation"),
        ),
    )

    assessment = RotationUltimateAffordabilityAssessor().assess(plan, requirement)

    assert assessment.violations == ()
    assert assessment.ending_amount == 0.0


def test_same_time_ultimate_actions_consume_shared_pool_in_plan_order() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Barrier", bar="front"),
        RotationAction(10.0, 1, RotationActionKind.ULTIMATE, "Aggressive Horn", bar="back"),
    )
    requirement = RotationUltimateAffordabilityRequirement(
        starting_amount=300.0,
        spend_rules=(
            UltimateSpendRule("Barrier", 250.0),
            UltimateSpendRule("Aggressive Horn", 250.0),
        ),
    )

    assessment = RotationUltimateAffordabilityAssessor().assess(plan, requirement)

    assert tuple(item.action_name for item in assessment.violations) == ("Aggressive Horn",)
    assert assessment.violations[0].balance_before == 50.0


def test_unresolved_ultimate_identity_is_not_guessed() -> None:
    plan = _plan(
        RotationAction(10.0, 0, RotationActionKind.ULTIMATE, "Unknown Ultimate", bar="front"),
    )
    requirement = RotationUltimateAffordabilityRequirement(
        starting_amount=0.0,
        spend_rules=(UltimateSpendRule("Barrier", 250.0),),
    )

    assessment = RotationUltimateAffordabilityAssessor().assess(plan, requirement)

    assert assessment.violations == ()
    assert assessment.ending_amount == 0.0
