from services.rotation_reviewed_execute_amplification_service import (
    RotationReviewedExecuteAmplificationService,
)


def test_killers_blade_linear_execute_scaling() -> None:
    service = RotationReviewedExecuteAmplificationService()

    at_threshold = service.resolve_multiplier(
        skill_name="Killer's Blade",
        health_fraction=0.50,
        threshold=0.50,
        maximum_bonus_fraction=4.0,
    )
    halfway = service.resolve_multiplier(
        skill_name="Killer's Blade",
        health_fraction=0.25,
        threshold=0.50,
        maximum_bonus_fraction=4.0,
    )
    zero = service.resolve_multiplier(
        skill_name="Killer's Blade",
        health_fraction=0.0,
        threshold=0.50,
        maximum_bonus_fraction=4.0,
    )

    assert at_threshold.damage_multiplier == 1.0
    assert halfway.damage_multiplier == 3.0
    assert zero.damage_multiplier == 5.0


def test_unreviewed_up_to_execute_remains_unresolved() -> None:
    result = RotationReviewedExecuteAmplificationService().resolve_multiplier(
        skill_name="Executioner",
        health_fraction=0.25,
        threshold=0.50,
        maximum_bonus_fraction=4.0,
    )

    assert result.resolved is False
    assert result.damage_multiplier is None
    assert "not source-reviewed" in result.unresolved[0]


def test_reviewed_execute_requires_maximum_bonus_evidence() -> None:
    result = RotationReviewedExecuteAmplificationService().resolve_multiplier(
        skill_name="Killer's Blade",
        health_fraction=0.25,
        threshold=0.50,
        maximum_bonus_fraction=None,
    )

    assert result.resolved is False
    assert "maximum bonus evidence" in result.unresolved[0]
