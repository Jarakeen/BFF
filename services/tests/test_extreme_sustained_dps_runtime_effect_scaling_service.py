from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_target_type import SupportTargetType
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_runtime_effect_scaling_service import (
    ExtremeSustainedDPSRuntimeEffectScalingService,
)


def _master_architect() -> EffectVariant:
    return EffectVariant(
        name="major_slayer",
        layer=EffectLayer.PROC,
        source="Master Architect (5)",
        magnitude=10.0,
        duration=1.0,
        scaling="1 second per 10 Ultimate spent",
        trigger="ultimate_activation_in_combat",
        target_type=SupportTargetType.GROUP,
    )


def _plan(*actions) -> RotationPlan:
    return RotationPlan(
        character_name="Generated",
        build_name="Candidate",
        duration_seconds=60.0,
        actions=tuple(actions),
    )


class _UltimateService:
    def __init__(self, costs):
        self.costs = dict(costs)

    def resolve_generation_inputs(self, *, ultimate_bar, **_kwargs):
        cost = self.costs.get(ultimate_bar)
        return SimpleNamespace(
            spend_rule=(
                None
                if cost is None
                else SimpleNamespace(cost=float(cost))
            ),
            unresolved=(),
        )


def test_master_architect_duration_resolves_from_canonical_ultimate_spend() -> None:
    result = ExtremeSustainedDPSRuntimeEffectScalingService(
        ultimate_service=_UltimateService({"front": 250.0}),
    ).resolve(
        build=PlayerBuild(),
        plan=_plan(
            RotationAction(
                10.0,
                0,
                RotationActionKind.ULTIMATE,
                "Aggressive Horn",
                "front",
            )
        ),
        effects=(_master_architect(),),
    )

    assert result.unresolved == ()
    assert len(result.effects) == 1
    effect = result.effects[0]
    assert effect.duration == 25.0
    assert effect.scaling is None
    assert any("250 / 10 = 25s" in row for row in result.evidence)


def test_master_architect_without_scheduled_ultimate_keeps_scaling_visible() -> None:
    original = _master_architect()
    result = ExtremeSustainedDPSRuntimeEffectScalingService(
        ultimate_service=_UltimateService({"front": 250.0}),
    ).resolve(
        build=PlayerBuild(),
        plan=_plan(),
        effects=(original,),
    )

    assert result.unresolved == ()
    assert len(result.effects) == 1
    assert result.effects[0].name == original.name
    assert result.effects[0].scaling is None
    assert any("no scheduled Ultimate activation" in row for row in result.evidence)


def test_master_architect_mixed_ultimate_costs_fail_closed() -> None:
    result = ExtremeSustainedDPSRuntimeEffectScalingService(
        ultimate_service=_UltimateService(
            {
                "front": 250.0,
                "back": 200.0,
            }
        ),
    ).resolve(
        build=PlayerBuild(),
        plan=_plan(
            RotationAction(
                10.0,
                0,
                RotationActionKind.ULTIMATE,
                "Front Ultimate",
                "front",
            ),
            RotationAction(
                30.0,
                0,
                RotationActionKind.ULTIMATE,
                "Back Ultimate",
                "back",
            ),
        ),
        effects=(_master_architect(),),
    )

    assert result.effects == ()
    assert any("different costs" in row for row in result.unresolved)


def test_unreviewed_runtime_scaling_fails_closed_before_relevance() -> None:
    alkosh = EffectVariant(
        name="roar_of_alkosh",
        layer=EffectLayer.PROC,
        source="Roar of Alkosh (5)",
        duration=10.0,
        scaling="Weapon Damage, up to 6000 resistance reduction",
        trigger="synergy_activation",
        target_type=SupportTargetType.ENEMY,
        resistance_reduction=6000.0,
    )

    result = ExtremeSustainedDPSRuntimeEffectScalingService(
        ultimate_service=_UltimateService({}),
    ).resolve(
        build=PlayerBuild(),
        plan=_plan(),
        effects=(alkosh,),
    )

    assert result.effects == ()
    assert result.resolved is False
    assert any(
        "Roar of Alkosh (5) roar_of_alkosh runtime scaling is not reviewed" in row
        for row in result.unresolved
    )


def test_unscaled_runtime_effect_passes_through_unchanged() -> None:
    effect = EffectVariant(
        name="major_courage",
        layer=EffectLayer.PROC,
        source="Test",
        magnitude=430.0,
        duration=10.0,
        trigger="damage_dealt",
        target_type=SupportTargetType.SELF,
    )

    result = ExtremeSustainedDPSRuntimeEffectScalingService(
        ultimate_service=_UltimateService({}),
    ).resolve(
        build=PlayerBuild(),
        plan=_plan(),
        effects=(effect,),
    )

    assert result.effects == (effect,)
    assert result.unresolved == ()
