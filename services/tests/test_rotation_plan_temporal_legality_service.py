from __future__ import annotations

from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_plan_temporal_legality_service import (
    RotationPlanTemporalLegalityService,
)
from services.rotation_temporal_effect_uptime_service import (
    RotationTemporalEffectApplication,
)


def _plan(*actions: RotationAction) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="Temporal Plan Build",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


def _app(
    *,
    time: float,
    layer: EffectLayer,
    source: str,
    bar: str,
    effect: str = "effect",
) -> RotationTemporalEffectApplication:
    return RotationTemporalEffectApplication(
        time_seconds=time,
        effect_name=effect,
        layer=layer,
        source=source,
        bar=bar,
    )


def test_proc_activation_matches_reconstructed_active_bar() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(
            RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        ),
        applications=(
            _app(time=5.0, layer=EffectLayer.PROC, source="Set Proc", bar="front"),
            _app(time=15.0, layer=EffectLayer.PROC, source="Set Proc", bar="back"),
        ),
        initial_bar="front",
    )

    assert assessment.is_legal is True
    assert assessment.violations == ()
    assert assessment.unresolved == ()


def test_wrong_claimed_bar_is_plan_legality_violation() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(
            RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        ),
        applications=(
            _app(time=15.0, layer=EffectLayer.PROC, source="Set Proc", bar="front"),
        ),
        initial_bar="front",
    )

    assert assessment.is_legal is False
    assert len(assessment.violations) == 1
    assert "plan has back bar active" in assessment.violations[0].reason


def test_same_timestamp_swap_keeps_bar_evidence_unresolved() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(
            RotationAction(10.0, 0, RotationActionKind.BAR_SWAP, bar="back"),
        ),
        applications=(
            _app(time=10.0, layer=EffectLayer.PROC, source="Set Proc", bar="back"),
        ),
        initial_bar="front",
    )

    assert assessment.is_legal is False
    assert assessment.violations == ()
    assert "same timestamp" in assessment.unresolved[0]


def test_ultimate_activation_requires_matching_scheduled_ultimate_action() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(
            RotationAction(
                20.0,
                0,
                RotationActionKind.ULTIMATE,
                name="Aggressive Horn",
                bar="front",
            ),
        ),
        applications=(
            _app(
                time=20.0,
                layer=EffectLayer.ULTIMATE,
                source="Aggressive Horn",
                bar="front",
                effect="major_force",
            ),
        ),
        initial_bar="front",
    )

    assert assessment.is_legal is True


def test_ultimate_activation_without_matching_plan_action_is_illegal() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(),
        applications=(
            _app(
                time=20.0,
                layer=EffectLayer.ULTIMATE,
                source="Aggressive Horn",
                bar="front",
                effect="major_force",
            ),
        ),
        initial_bar="front",
    )

    assert assessment.is_legal is False
    assert "requires exactly one matching scheduled ultimate action" in assessment.violations[0].reason


def test_consumable_activation_requires_matching_potion_action() -> None:
    legal = RotationPlanTemporalLegalityService().assess(
        plan=_plan(
            RotationAction(
                12.0,
                0,
                RotationActionKind.POTION,
                name="Essence of Spell Power",
                bar="front",
            ),
        ),
        applications=(
            _app(
                time=12.0,
                layer=EffectLayer.CONSUMABLE,
                source="Essence of Spell Power",
                bar="front",
            ),
        ),
        initial_bar="front",
    )
    illegal = RotationPlanTemporalLegalityService().assess(
        plan=_plan(),
        applications=(
            _app(
                time=12.0,
                layer=EffectLayer.CONSUMABLE,
                source="Essence of Spell Power",
                bar="front",
            ),
        ),
        initial_bar="front",
    )

    assert legal.is_legal is True
    assert illegal.is_legal is False
    assert "requires exactly one matching scheduled potion action" in illegal.violations[0].reason


def test_initial_bar_is_explicit_not_inferred() -> None:
    assessment = RotationPlanTemporalLegalityService().assess(
        plan=_plan(),
        applications=(
            _app(time=1.0, layer=EffectLayer.PROC, source="Set Proc", bar="back"),
        ),
        initial_bar="back",
    )

    assert assessment.is_legal is True
