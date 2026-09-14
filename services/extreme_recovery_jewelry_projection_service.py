from __future__ import annotations

"""Project canonical Recovery jewelry glyphs with reviewed Gold Infused scaling."""

from dataclasses import dataclass

from minmax.effects import EffectOperation, EffectUnit
from minmax.jewelry_glyph_repository import JewelryGlyphEffectRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.stat_ids import StatId


_TARGETS = {
    "health_recovery": ("health_recovery", StatId.HEALTH_RECOVERY),
    "magicka_recovery": ("magicka_recovery", StatId.MAGICKA_RECOVERY),
    "stamina_recovery": ("stamina_recovery", StatId.STAMINA_RECOVERY),
}


@dataclass(frozen=True)
class ExtremeRecoveryJewelryProjection:
    objective_key: str
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


class ExtremeRecoveryJewelryProjectionService:
    """Find the strongest canonical Recovery glyph and Gold Infused scaling."""

    def __init__(
        self,
        glyph_repository: JewelryGlyphEffectRepository,
        trait_repository: JewelryTraitRepository,
    ) -> None:
        self.glyph_repository = glyph_repository
        self.trait_repository = trait_repository

    def build(self, objective_key: str) -> ExtremeRecoveryJewelryProjection:
        objective = str(objective_key or "").strip().casefold()
        target = _TARGETS.get(objective)
        if target is None:
            return ExtremeRecoveryJewelryProjection(
                objective_key=objective,
                glyphs_reviewed=0,
                relevant_glyphs=(),
                strongest_glyph_name=None,
                base_flat_per_slot=None,
                infused_percent=None,
                infused_flat_per_slot=None,
                three_slot_infused_flat=None,
                unresolved=(f"Unsupported Recovery jewelry objective: {objective_key!r}",),
            )
        target_effect_type, target_stat = target

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
            if target_effect_type not in effect_types:
                continue

            effects = tuple(
                self.glyph_repository.get_jewelry_glyph_effect_by_name(
                    name,
                    use_max_value=True,
                )
            )
            target_effects = tuple(effect for effect in effects if effect.stat is target_stat)
            if not target_effects:
                unresolved.append(
                    f"{objective} jewelry glyph has semantic identity but no mapped target effect: {name}"
                )
                continue

            total = 0.0
            local_problem = False
            for effect in target_effects:
                if effect.operation is not EffectOperation.ADD or effect.unit is not EffectUnit.FLAT:
                    unresolved.append(
                        f"{objective} jewelry glyph requires flat additive semantics: {name}"
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
            unresolved.append(f"No canonical {objective} jewelry glyph was resolved")

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

        return ExtremeRecoveryJewelryProjection(
            objective_key=objective,
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
    "ExtremeRecoveryJewelryProjection",
    "ExtremeRecoveryJewelryProjectionService",
]
