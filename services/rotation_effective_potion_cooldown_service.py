from __future__ import annotations

from dataclasses import dataclass
import math

from minmax.potion_cadence import BASE_POTION_COOLDOWN_SECONDS
from services.rotation_potion_cooldown_effect_variant_service import (
    RotationPotionCooldownEffectEvidence,
)
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemEvidence,
)


@dataclass(frozen=True)
class RotationEffectivePotionCooldownEvidence:
    """Complete-or-partial evidence for one build's potion cooldown.

    ``effective_cooldown_seconds`` is populated only when every contribution source
    in the caller's canonical non-item effect inventory is proven complete and all
    item/non-item evidence is resolved. This prevents a known jewelry contribution
    from being mistaken for a globally complete build cadence.
    """

    base_cooldown_seconds: float
    item_reduction_seconds: float
    effect_reduction_seconds: float
    effective_cooldown_seconds: float | None
    effect_inventory_complete: bool
    unresolved: tuple[str, ...] = ()

    @property
    def total_reduction_seconds(self) -> float:
        return self.item_reduction_seconds + self.effect_reduction_seconds

    @property
    def complete(self) -> bool:
        return self.effective_cooldown_seconds is not None and not self.unresolved


class RotationEffectivePotionCooldownService:
    """Aggregate verified item and canonical effect cooldown contributions.

    The default base cooldown comes from the existing potion cadence model. Callers
    may override it only with already-verified scenario evidence. This service owns
    aggregation and completeness checks, not discovery of ESO mechanics.
    """

    def resolve(
        self,
        *,
        item_evidence: RotationSavedBuildPotionCooldownItemEvidence,
        effect_evidence: RotationPotionCooldownEffectEvidence,
        effect_inventory_complete: bool,
        base_cooldown_seconds: float = BASE_POTION_COOLDOWN_SECONDS,
    ) -> RotationEffectivePotionCooldownEvidence:
        base = float(base_cooldown_seconds)
        if not math.isfinite(base) or base <= 0.0:
            raise ValueError("base potion cooldown must be finite and positive")

        unresolved = list(item_evidence.unresolved) + list(effect_evidence.unresolved)
        if not effect_inventory_complete:
            unresolved.append(
                "canonical non-item potion cooldown effect inventory is not proven complete"
            )

        item_reduction = float(item_evidence.total_reduction_seconds)
        effect_reduction = float(effect_evidence.total_reduction_seconds)
        total_reduction = item_reduction + effect_reduction
        if not math.isfinite(total_reduction) or total_reduction < 0.0:
            unresolved.append("total potion cooldown reduction is invalid")

        effective: float | None = None
        if not unresolved:
            candidate = base - total_reduction
            if candidate <= 0.0:
                unresolved.append(
                    "resolved potion cooldown reduction is greater than or equal to the base cooldown"
                )
            else:
                effective = candidate

        return RotationEffectivePotionCooldownEvidence(
            base_cooldown_seconds=base,
            item_reduction_seconds=item_reduction,
            effect_reduction_seconds=effect_reduction,
            effective_cooldown_seconds=effective,
            effect_inventory_complete=bool(effect_inventory_complete),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "RotationEffectivePotionCooldownEvidence",
    "RotationEffectivePotionCooldownService",
]
