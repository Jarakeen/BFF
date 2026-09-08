from __future__ import annotations

from dataclasses import dataclass

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.passive_grant import PassiveGrant
from services.rotation_effective_potion_cooldown_service import (
    RotationEffectivePotionCooldownEvidence,
    RotationEffectivePotionCooldownService,
)
from services.rotation_potion_cooldown_effect_inventory_service import (
    RotationPotionCooldownEffectInventory,
    RotationPotionCooldownEffectInventoryService,
)
from services.rotation_potion_cooldown_effect_variant_service import (
    RotationPotionCooldownEffectEvidence,
    RotationPotionCooldownEffectVariantService,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemEvidence,
)


@dataclass(frozen=True)
class RotationBuildPotionCooldownResolution:
    """End-to-end potion-cooldown evidence for one build/context."""

    inventory: RotationPotionCooldownEffectInventory
    effect_evidence: RotationPotionCooldownEffectEvidence
    effective: RotationEffectivePotionCooldownEvidence


class RotationBuildPotionCooldownService:
    """Compose canonical build/context inventory into effective potion cadence.

    The service owns plumbing only. Item values, EffectVariant semantics, and final
    arithmetic remain in their dedicated resolvers. An effective cooldown is emitted
    only when the inventory itself certifies completeness.
    """

    def __init__(
        self,
        *,
        inventory_service: RotationPotionCooldownEffectInventoryService | None = None,
        effect_service: RotationPotionCooldownEffectVariantService | None = None,
        effective_service: RotationEffectivePotionCooldownService | None = None,
    ) -> None:
        self.inventory_service = inventory_service or RotationPotionCooldownEffectInventoryService()
        self.effect_service = effect_service or RotationPotionCooldownEffectVariantService()
        self.effective_service = effective_service or RotationEffectivePotionCooldownService()

    def resolve(
        self,
        *,
        character_build: CharacterBuild,
        item_evidence: RotationSavedBuildPotionCooldownItemEvidence,
        passives: tuple[PassiveGrant, ...] = (),
        scenario_effects: tuple[EffectVariant, ...] = (),
        scenario_inventory_complete: bool = False,
        base_cooldown_seconds: float | None = None,
    ) -> RotationBuildPotionCooldownResolution:
        inventory = self.inventory_service.resolve(
            character_build=character_build,
            passives=passives,
            scenario_effects=scenario_effects,
            scenario_inventory_complete=scenario_inventory_complete,
        )
        resolved_effects = self.effect_service.resolve(inventory.effects)
        effect_evidence = RotationPotionCooldownEffectEvidence(
            reductions=resolved_effects.reductions,
            unresolved=tuple(
                dict.fromkeys(inventory.unresolved + resolved_effects.unresolved)
            ),
        )

        kwargs = dict(
            item_evidence=item_evidence,
            effect_evidence=effect_evidence,
            effect_inventory_complete=inventory.complete,
        )
        if base_cooldown_seconds is not None:
            kwargs["base_cooldown_seconds"] = base_cooldown_seconds

        effective = self.effective_service.resolve(**kwargs)
        return RotationBuildPotionCooldownResolution(
            inventory=inventory,
            effect_evidence=effect_evidence,
            effective=effective,
        )


__all__ = [
    "RotationBuildPotionCooldownResolution",
    "RotationBuildPotionCooldownService",
]
