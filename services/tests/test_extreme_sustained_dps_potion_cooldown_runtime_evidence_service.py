from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.extreme_sustained_dps_potion_cooldown_runtime_evidence_service import (
    ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService,
)
from services.rotation_potion_cooldown_effect_variant_service import (
    POTION_COOLDOWN_REDUCTION_EFFECT,
)


def _effect(name: str) -> EffectVariant:
    return EffectVariant(
        name=name,
        layer=EffectLayer.PASSIVE,
        source="test",
        magnitude=3.0,
    )


def test_proven_runtime_denominator_can_prove_absence_of_cooldown_effects() -> None:
    result = ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService.resolve(
        effects=(_effect("unrelated"),),
        denominator_proven=True,
    )

    assert result.scenario.complete
    assert result.scenario.effects == ()
    assert result.unresolved == ()


def test_proven_runtime_denominator_retains_only_cooldown_effects() -> None:
    cooldown = _effect(POTION_COOLDOWN_REDUCTION_EFFECT)
    result = ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService.resolve(
        effects=(_effect("unrelated"), cooldown),
        denominator_proven=True,
    )

    assert result.scenario.complete
    assert result.scenario.effects == (cooldown,)


def test_open_runtime_denominator_cannot_prove_potion_cooldown_scenario() -> None:
    result = ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService.resolve(
        effects=(),
        denominator_proven=False,
    )

    assert not result.scenario.complete
    assert result.unresolved == ("Runtime effect denominator is not proven complete",)


def test_runtime_unresolved_evidence_forces_potion_cooldown_open() -> None:
    result = ExtremeSustainedDPSPotionCooldownRuntimeEvidenceService.resolve(
        effects=(_effect(POTION_COOLDOWN_REDUCTION_EFFECT),),
        denominator_proven=True,
        unresolved=("conditional set topology unresolved",),
    )

    assert not result.scenario.complete
    assert result.unresolved == ("conditional set topology unresolved",)
