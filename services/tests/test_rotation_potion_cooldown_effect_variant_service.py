from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId, EffectLayer
from services.rotation_potion_cooldown_effect_variant_service import (
    RotationPotionCooldownEffectVariantService,
)


def _effect(**overrides) -> EffectVariant:
    values = dict(
        name="potion_cooldown_reduction",
        layer=EffectLayer.PASSIVE,
        source="Verified passive",
        magnitude=3.0,
    )
    values.update(overrides)
    return EffectVariant(**values)


def test_unconditional_canonical_reductions_are_summed_across_skill_and_set_layers() -> None:
    evidence = RotationPotionCooldownEffectVariantService().resolve(
        (
            _effect(source="Passive source", magnitude=3.0, layer=EffectLayer.PASSIVE),
            _effect(source="Set source", magnitude=2.0, layer=EffectLayer.PROC),
            EffectVariant(
                name="unrelated_effect",
                layer=EffectLayer.PASSIVE,
                source="Other",
                magnitude=99.0,
            ),
        )
    )

    assert evidence.total_reduction_seconds == 5.0
    assert [(item.source, item.seconds, item.layer) for item in evidence.reductions] == [
        ("Passive source", 3.0, "passive"),
        ("Set source", 2.0, "proc"),
    ]
    assert evidence.unresolved == ()


def test_runtime_dependent_variants_remain_unresolved_instead_of_becoming_static_cadence() -> None:
    evidence = RotationPotionCooldownEffectVariantService().resolve(
        (
            _effect(source="Conditional", condition="while transformed"),
            _effect(source="Triggered", trigger="after ultimate cast"),
            _effect(source="Bar scoped", active_bar=BarId.BACK),
            _effect(source="Stochastic", chance=0.5),
        )
    )

    assert evidence.reductions == ()
    assert len(evidence.unresolved) == 4
    assert any("Conditional" in item and "condition=" in item for item in evidence.unresolved)
    assert any("Triggered" in item and "trigger=" in item for item in evidence.unresolved)
    assert any("Bar scoped" in item and "active_bar=back" in item for item in evidence.unresolved)
    assert any("Stochastic" in item and "chance=0.5" in item for item in evidence.unresolved)


def test_ineligible_effect_is_known_not_to_contribute_and_missing_magnitude_fails_closed() -> None:
    evidence = RotationPotionCooldownEffectVariantService().resolve(
        (
            _effect(source="Inactive source", eligible=False),
            _effect(source="Missing magnitude", magnitude=None),
        )
    )

    assert evidence.reductions == ()
    assert evidence.unresolved == (
        "canonical potion cooldown reduction cannot be folded into static cadence: Missing magnitude (magnitude missing)",
    )
