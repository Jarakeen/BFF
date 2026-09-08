from __future__ import annotations

"""Resolve jewelry-enchantment contributions for Extreme/MOST Bash.

The mined jewelry-glyph tables remain the source of truth. This service projects
only the Bash-specific item channel needed by the canonical Bash equation and
keeps Infused scaling explicit. Unrelated jewelry enchants are valid choices and
contribute zero to this objective; a selected Bashing enchant with missing or
unreviewable source data remains an explicit blocker.
"""

from dataclasses import dataclass

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


@dataclass(frozen=True)
class ExtremeBashJewelrySlotResult:
    slot_name: str
    enchant: str
    reviewed_item_extra_bash_damage: float
    source_effects: tuple[Effect, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


@dataclass(frozen=True)
class ExtremeBashJewelryResult:
    reviewed_item_extra_bash_damage: float
    slots: tuple[ExtremeBashJewelrySlotResult, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def mechanic_complete(self) -> bool:
        return not self.unresolved


class ExtremeBashJewelryService:
    """Project saved jewelry enchantments into ``Item.ExtraBashDamage``."""

    BASH_ENCHANT_LABELS = frozenset({"bashing"})

    def __init__(
        self,
        glyph_repository: JewelryGlyphEffectRepository,
        trait_repository: JewelryTraitRepository | None = None,
    ) -> None:
        self.glyph_repository = glyph_repository
        self.trait_repository = trait_repository

    def _infused_multiplier(
        self,
        slot_name: str,
        slot: GearSlot,
    ) -> tuple[float | None, str | None]:
        if str(slot.Trait or "").strip().casefold() != "infused":
            return 1.0, None
        if self.trait_repository is None:
            return None, f"{slot_name}: Infused jewelry trait repository unavailable"
        quality = str(slot.Quality or "").strip()
        percent = self.trait_repository.get_infused_enchantment_percent(quality)
        if percent is None:
            return None, (
                f"{slot_name}: Infused jewelry value unavailable for quality "
                f"{quality or 'unset'}"
            )
        return 1.0 + (float(percent) / 100.0), None

    def evaluate_slot(
        self,
        slot_name: str,
        slot: GearSlot,
    ) -> ExtremeBashJewelrySlotResult:
        enchant = str(slot.Enchant or "").strip()
        if enchant.casefold() not in self.BASH_ENCHANT_LABELS:
            return ExtremeBashJewelrySlotResult(
                slot_name=slot_name,
                enchant=enchant,
                reviewed_item_extra_bash_damage=0.0,
            )

        unresolved: list[str] = []
        level = str(slot.Level or "").strip()
        tier = str(slot.EnchantTier or "").strip()
        if level.casefold() != "cp160" or tier.casefold() != "truly superb":
            unresolved.append(
                f"{slot_name} Bashing: needs verified level/tier scaling "
                f"({level or 'level unset'}, {tier or 'tier unset'})"
            )

        multiplier, multiplier_problem = self._infused_multiplier(slot_name, slot)
        if multiplier_problem:
            unresolved.append(multiplier_problem)

        try:
            effects = tuple(
                self.glyph_repository.get_strongest_jewelry_glyph_effect_by_type(
                    "bash_damage",
                    use_max_value=True,
                )
            )
        except ValueError as exc:
            return ExtremeBashJewelrySlotResult(
                slot_name=slot_name,
                enchant=enchant,
                reviewed_item_extra_bash_damage=0.0,
                unresolved=tuple(unresolved + [f"{slot_name} Bashing: {exc}"]),
            )

        if not effects:
            unresolved.append(f"{slot_name} Bashing: canonical bash_damage jewelry glyph not found")
            return ExtremeBashJewelrySlotResult(
                slot_name=slot_name,
                enchant=enchant,
                reviewed_item_extra_bash_damage=0.0,
                unresolved=tuple(unresolved),
            )

        reviewed = 0.0
        for effect in effects:
            if effect.stat is not StatId.BASH_DAMAGE:
                unresolved.append(
                    f"{slot_name} Bashing: unexpected glyph stat "
                    f"{effect.stat.value if effect.stat else 'unknown'}"
                )
                continue
            if effect.operation is not EffectOperation.ADD or effect.unit is not EffectUnit.FLAT:
                unresolved.append(
                    f"{slot_name} Bashing: bash_damage glyph requires reviewed flat additive semantics"
                )
                continue
            if multiplier is not None:
                reviewed += float(effect.value) * multiplier

        return ExtremeBashJewelrySlotResult(
            slot_name=slot_name,
            enchant=enchant,
            reviewed_item_extra_bash_damage=reviewed,
            source_effects=effects,
            unresolved=tuple(unresolved),
        )

    def evaluate_build(self, build: PlayerBuild) -> ExtremeBashJewelryResult:
        slots = tuple(
            self.evaluate_slot(slot_name, slot)
            for slot_name, slot in (
                ("Necklace", build.Necklace),
                ("Ring 1", build.Ring1),
                ("Ring 2", build.Ring2),
            )
        )
        unresolved = tuple(
            problem
            for slot in slots
            for problem in slot.unresolved
        )
        return ExtremeBashJewelryResult(
            reviewed_item_extra_bash_damage=sum(
                slot.reviewed_item_extra_bash_damage for slot in slots
            ),
            slots=slots,
            unresolved=unresolved,
        )
