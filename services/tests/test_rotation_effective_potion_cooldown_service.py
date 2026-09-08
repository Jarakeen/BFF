from minmax.jewelry_potion_cooldown_repository import JewelryPotionCooldownReduction
from services.rotation_effective_potion_cooldown_service import (
    RotationEffectivePotionCooldownService,
)
from services.rotation_potion_cooldown_effect_variant_service import (
    RotationPotionCooldownEffectEvidence,
    RotationPotionCooldownEffectReduction,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemEvidence,
)


def test_complete_item_and_effect_inventory_produces_effective_cooldown() -> None:
    evidence = RotationEffectivePotionCooldownService().resolve(
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(
            reductions=(JewelryPotionCooldownReduction("Ring 1", 8.0),),
        ),
        effect_evidence=RotationPotionCooldownEffectEvidence(
            reductions=(
                RotationPotionCooldownEffectReduction(
                    source="Verified passive",
                    seconds=2.0,
                    layer="passive",
                ),
            ),
        ),
        effect_inventory_complete=True,
    )

    assert evidence.item_reduction_seconds == 8.0
    assert evidence.effect_reduction_seconds == 2.0
    assert evidence.total_reduction_seconds == 10.0
    assert evidence.effective_cooldown_seconds == 35.0
    assert evidence.complete
    assert evidence.unresolved == ()


def test_incomplete_non_item_inventory_never_claims_effective_cooldown() -> None:
    evidence = RotationEffectivePotionCooldownService().resolve(
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(
            reductions=(JewelryPotionCooldownReduction("Necklace", 5.0),),
        ),
        effect_evidence=RotationPotionCooldownEffectEvidence(),
        effect_inventory_complete=False,
    )

    assert evidence.total_reduction_seconds == 5.0
    assert evidence.effective_cooldown_seconds is None
    assert not evidence.complete
    assert evidence.unresolved == (
        "canonical non-item potion cooldown effect inventory is not proven complete",
    )


def test_unresolved_item_or_effect_evidence_prevents_effective_cooldown() -> None:
    evidence = RotationEffectivePotionCooldownService().resolve(
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(
            unresolved=("item ambiguity",),
        ),
        effect_evidence=RotationPotionCooldownEffectEvidence(
            unresolved=("conditional set contribution",),
        ),
        effect_inventory_complete=True,
    )

    assert evidence.effective_cooldown_seconds is None
    assert evidence.unresolved == (
        "item ambiguity",
        "conditional set contribution",
    )


def test_total_reduction_cannot_consume_entire_base_cooldown() -> None:
    evidence = RotationEffectivePotionCooldownService().resolve(
        item_evidence=RotationSavedBuildPotionCooldownItemEvidence(
            reductions=(JewelryPotionCooldownReduction("Impossible", 45.0),),
        ),
        effect_evidence=RotationPotionCooldownEffectEvidence(),
        effect_inventory_complete=True,
    )

    assert evidence.effective_cooldown_seconds is None
    assert evidence.unresolved == (
        "resolved potion cooldown reduction is greater than or equal to the base cooldown",
    )
