from __future__ import annotations

"""Project canonical Health Recovery jewelry glyphs with reviewed Infused scaling."""

from dataclasses import dataclass

from minmax.effects import EffectOperation, EffectUnit
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId


@dataclass(frozen=True)
class ExtremeHealthRecoveryJewelryProjection:
    glyphs_reviewed: int
    relevant_glyphs: tuple[str, ...]
    strongest_glyph_name: str | None
    base_flat_per_slot: float | None
    infused_percent: float | None
    infused_flat_per_slot: float | None
    three_slot_infused_flat: float | None
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        return bool(self.glyphs_reviewed and self.strongest_glyph_name and not self.unresolved)


class ExtremeHealthRecoveryJewelryProjectionService:
    """Find the strongest canonical Health Recovery glyph and Gold Infused scaling."""

    TARGET_EFFECT_TYPE = "health_recovery"

    def __init__(
        self,
        glyph_repository: JewelryGlyphEffectRepository,
        trait_repository: JewelryTraitRepository,
    ) -> None:
        self.glyph_repository = glyph_repository
        self.trait_repository = trait_repository

    def build(self) -> ExtremeHealthRecoveryJewelryProjection:
        names = tuple(
            dict.fromkeys(
                str(name or "").strip()
                for name in self.glyph_repository.list_names()
                if str(name or "").strip()
            )
        )
        unresolved: list[str] = []
        relevant: list[tuple[str, float]] = []

        if not names:
            unresolved.append("Canonical jewelry glyph catalog is empty")

        for name in names:
            effect_types = tuple(
                str(value or "").strip().casefold()
                for value in self.glyph_repository.get_jewelry_glyph_effect_types_by_name(name)
                if str(value or "").strip()
            )
            if self.TARGET_EFFECT_TYPE not in effect_types:
                continue

            effects = tuple(
                self.glyph_repository.get_jewelry_glyph_effect_by_name(
                    name,
                    use_max_value=True,
                )
            )
            target_effects = tuple(effect for effect in effects if effect.stat is StatId.HEALTH_RECOVERY)
            if not target_effects:
                unresolved.append(
                    f"Health Recovery jewelry glyph has semantic identity but no mapped target effect: {name}"
                )
                continue

            total = 0.0
            local_problem = False
            for effect in target_effects:
                if effect.operation is not EffectOperation.ADD or effect.unit is not EffectUnit.FLAT:
                    unresolved.append(
                        f"Health Recovery jewelry glyph requires flat additive semantics: {name}"
                    )
                    local_problem = True
                    continue
                total += float(effect.value)
            if not local_problem:
                relevant.append((name, total))

        relevant.sort(key=lambda row: (-row[1], row[0].casefold()))
        strongest_name = relevant[0][0] if relevant else None
        base_flat = relevant[0][1] if relevant else None
        if not relevant:
            unresolved.append("No canonical Health Recovery jewelry glyph was resolved")

        infused_percent = self.trait_repository.get_infused_enchantment_percent("Gold")
        if infused_percent is None:
            unresolved.append("Gold Infused jewelry enchantment percent is unavailable")
            infused_flat = None
            three_slot = None
        elif base_flat is None:
            infused_flat = None
            three_slot = None
        else:
            infused_flat = float(base_flat) * (1.0 + float(infused_percent) / 100.0)
            three_slot = infused_flat * 3.0

        return ExtremeHealthRecoveryJewelryProjection(
            glyphs_reviewed=len(names),
            relevant_glyphs=tuple(name for name, _ in relevant),
            strongest_glyph_name=strongest_name,
            base_flat_per_slot=base_flat,
            infused_percent=infused_percent,
            infused_flat_per_slot=infused_flat,
            three_slot_infused_flat=three_slot,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeHealthRecoveryJewelryProjection",
    "ExtremeHealthRecoveryJewelryProjectionService",
]
