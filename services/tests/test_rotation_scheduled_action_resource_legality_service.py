from __future__ import annotations

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent, UltimateSpendRule
from services.rotation_scheduled_action_resource_legality_service import (
    RotationScheduledActionResourceLegalityService,
)


def _plan(*actions: RotationAction, duration: float = 120.0) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Resource Legality Build",
        duration_seconds=duration,
        actions=tuple(actions),
    )


def _ultimate(time: float, sequence: int = 0, name: str = "Aggressive Horn") -> RotationAction:
    return RotationAction(
        time_seconds=time,
        sequence=sequence,
        kind=RotationActionKind.ULTIMATE,
        name=name,
        bar="front",
    )


def _potion(time: float, sequence: int = 0, name: str = "Essence of Spell Power") -> RotationAction:
    return RotationAction(
        time_seconds=time,
        sequence=sequence,
        kind=RotationActionKind.POTION,
        name=name,
        bar="front",
    )


def _horn_rule(cost: float = 250.0) -> UltimateSpendRule:
    return UltimateSpendRule(skill_name="Aggressive Horn", cost=cost)


def test_scheduled_ultimate_spends_explicit_starting_and_generated_resource() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_ultimate(10.0), _ultimate(60.0)),
        starting_ultimate=250.0,
        ultimate_generation_events=(
            UltimateGenerationEvent(40.0, 250.0, "explicit generation"),
        ),
        ultimate_spend_rules=(_horn_rule(),),
    )

    assert assessment.is_legal is True
    assert assessment.violations == ()
    assert assessment.unresolved == ()
    assert assessment.ending_ultimate == pytest.approx(0.0)


def test_scheduled_ultimate_without_enough_resource_is_illegal() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_ultimate(10.0)),
        starting_ultimate=100.0,
        ultimate_spend_rules=(_horn_rule(),),
    )

    assert assessment.is_legal is False
    assert assessment.unresolved == ()
    assert len(assessment.violations) == 1
    assert "requires 250.000 Ultimate" in assessment.violations[0].reason
    assert "100.000 is available" in assessment.violations[0].reason


def test_missing_ultimate_spend_rule_stays_unresolved() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_ultimate(10.0)),
        starting_ultimate=500.0,
        ultimate_spend_rules=(),
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert "no explicit canonical spend rule" in assessment.unresolved[0]


def test_same_timestamp_generation_does_not_silently_precede_ultimate_spend() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_ultimate(10.0)),
        starting_ultimate=200.0,
        ultimate_generation_events=(
            UltimateGenerationEvent(10.0, 50.0, "same timestamp gain"),
        ),
        ultimate_spend_rules=(_horn_rule(),),
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert "affordable only if same-timestamp generation occurs first" in assessment.unresolved[0]
    assert assessment.ending_ultimate == pytest.approx(250.0)


def test_potion_uses_must_respect_canonical_base_cooldown() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_potion(0.0), _potion(30.0)),
    )

    assert assessment.is_legal is False
    assert len(assessment.violations) == 1
    assert "inside the 45.000s cooldown" in assessment.violations[0].reason


def test_explicit_effective_potion_cooldown_can_be_supplied_by_upstream_evidence() -> None:
    assessment = RotationScheduledActionResourceLegalityService().assess(
        plan=_plan(_potion(0.0), _potion(30.0)),
        potion_cooldown_seconds=30.0,
    )

    assert assessment.is_legal is True
    assert assessment.potion_cooldown_seconds == pytest.approx(30.0)


def test_duplicate_semantic_ultimate_spend_rules_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate Ultimate spend rule"):
        RotationScheduledActionResourceLegalityService().assess(
            plan=_plan(_ultimate(10.0)),
            starting_ultimate=500.0,
            ultimate_spend_rules=(
                UltimateSpendRule(skill_name="Aggressive Horn", cost=250.0),
                UltimateSpendRule(skill_name="aggressive-horn", cost=250.0),
            ),
        )


def test_generation_after_rotation_duration_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot occur after rotation duration"):
        RotationScheduledActionResourceLegalityService().assess(
            plan=_plan(duration=20.0),
            ultimate_generation_events=(
                UltimateGenerationEvent(25.0, 10.0, "late generation"),
            ),
        )
