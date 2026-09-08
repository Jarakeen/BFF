from __future__ import annotations

from dataclasses import dataclass

from minmax.jewelry_potion_cooldown_repository import (
    JewelryPotionCooldownReduction,
    JewelryPotionCooldownRepository,
)
from minmax.jewelry_trait_repository import JewelryTraitRepository
from models.build_model import GearSlot, PlayerBuild


@dataclass(frozen=True)
class RotationSavedBuildPotionCooldownItemEvidence:
    """Verified jewelry-item contribution to potion cooldown reduction.

    This is intentionally not an effective potion cooldown. The repo formula also
    permits skill and set channels, so Rotation Maker must not subtract only the
    jewelry contribution from the base cooldown and call the result complete.
    """

    reductions: tuple[JewelryPotionCooldownReduction, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def total_reduction_seconds(self) -> float:
        return sum(float(item.seconds) for item in self.reductions)


class RotationSavedBuildPotionCooldownItemService:
    """Resolve verified potion-cooldown jewelry evidence from one saved build.

    Max-level glyph values are only used when the saved slot explicitly says CP160
    and Truly Superb. Infused potency is resolved through the existing canonical
    jewelry-trait repository. Non-potion jewelry enchants are ignored here.
    """

    def __init__(
        self,
        repository: JewelryPotionCooldownRepository,
        jewelry_trait_repository: JewelryTraitRepository | None = None,
    ) -> None:
        self.repository = repository
        self.jewelry_trait_repository = jewelry_trait_repository

    def resolve(self, build: PlayerBuild) -> RotationSavedBuildPotionCooldownItemEvidence:
        reductions: list[JewelryPotionCooldownReduction] = []
        unresolved: list[str] = []

        for slot_name, slot in (
            ("Necklace", build.Necklace),
            ("Ring 1", build.Ring1),
            ("Ring 2", build.Ring2),
        ):
            enchant = str(slot.Enchant or "").strip()
            if not enchant:
                continue

            resolved = self.repository.get_by_name(enchant)
            if not resolved:
                normalized = enchant.casefold()
                if "potion" in normalized and (
                    "cooldown" in normalized or "speed" in normalized
                ):
                    unresolved.append(
                        f"{slot_name}: canonical potion cooldown glyph not found by exact saved name: {enchant}"
                    )
                continue

            level = str(slot.Level or "").strip()
            tier = str(slot.EnchantTier or "").strip()
            if level.casefold() != "cp160" or tier.casefold() != "truly superb":
                unresolved.append(
                    f"{slot_name} {enchant}: needs verified level/tier scaling "
                    f"({level or 'level unset'}, {tier or 'tier unset'})"
                )
                continue

            multiplier, trait_label = self._jewelry_multiplier(
                slot_name,
                slot,
                unresolved,
            )
            if multiplier == 0.0:
                continue

            scaled = self.repository.get_by_name(
                enchant,
                multiplier=multiplier,
                source_prefix=slot_name,
            )
            if trait_label:
                scaled = tuple(
                    JewelryPotionCooldownReduction(
                        source=f"{item.source}{trait_label}",
                        seconds=item.seconds,
                    )
                    for item in scaled
                )
            reductions.extend(scaled)

        return RotationSavedBuildPotionCooldownItemEvidence(
            reductions=tuple(reductions),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    def _jewelry_multiplier(
        self,
        slot_name: str,
        slot: GearSlot,
        unresolved: list[str],
    ) -> tuple[float, str]:
        trait = str(slot.Trait or "").strip()
        if trait.casefold() != "infused":
            return 1.0, ""

        if self.jewelry_trait_repository is None:
            unresolved.append(f"{slot_name}: Infused jewelry trait repository unavailable")
            return 0.0, ""

        quality = str(slot.Quality or "").strip()
        percent = self.jewelry_trait_repository.get_infused_enchantment_percent(quality)
        if percent is None:
            unresolved.append(
                f"{slot_name}: Infused jewelry value unavailable for quality {quality or 'unset'}"
            )
            return 0.0, ""

        return 1.0 + (percent / 100.0), f" (Infused +{percent:g}%)"


__all__ = [
    "RotationSavedBuildPotionCooldownItemEvidence",
    "RotationSavedBuildPotionCooldownItemService",
]
