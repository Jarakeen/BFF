from __future__ import annotations

"""Compose proof-safe resource armor weight and trait/glyph witnesses.

The resource armor search has two independently reviewed finite source families:

* legal seven-piece Light/Medium/Heavy loadouts, reduced by distinct armor-type
  count because that is the only reviewed max-resource continuation (Undaunted
  Mettle), and
* joint Divines/Infused + armor-glyph states, reduced by Divines count because
  Mundus is the only later interaction owned by that layer.

This adapter crosses those proof-preserving witnesses without adding ESO math.
It deliberately does not grant Undaunted Mettle or any armor passive.  Passive
ownership remains a separate Extreme denominator axis and final build scoring
continues through the canonical calculation pipeline.
"""

from dataclasses import dataclass

from models.build_model import PlayerBuild
from services.extreme_armor_resource_trait_glyph_state_service import (
    ExtremeArmorResourceTraitGlyphState,
    ExtremeArmorResourceTraitGlyphStateCatalog,
    ExtremeArmorResourceTraitGlyphStateService,
)
from services.extreme_armor_resource_weight_state_service import (
    ExtremeArmorResourceWeightState,
    ExtremeArmorResourceWeightStateCatalog,
    ExtremeArmorResourceWeightStateService,
)


@dataclass(frozen=True)
class ExtremeArmorResourceWeightTraitGlyphState:
    objective_key: str
    weight_state: ExtremeArmorResourceWeightState
    trait_glyph_state: ExtremeArmorResourceTraitGlyphState

    @property
    def armor_type_count(self) -> int:
        return self.weight_state.armor_type_count

    @property
    def divines_count(self) -> int:
        return self.trait_glyph_state.divines_count

    @property
    def infused_count(self) -> int:
        return self.trait_glyph_state.infused_count

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            tuple(self.weight_state.identity),
            tuple(self.trait_glyph_state.identity),
        )


@dataclass(frozen=True)
class ExtremeArmorResourceWeightTraitGlyphStateCatalog:
    objective_key: str
    states: tuple[ExtremeArmorResourceWeightTraitGlyphState, ...]
    weight_catalog: ExtremeArmorResourceWeightStateCatalog
    trait_glyph_catalog: ExtremeArmorResourceTraitGlyphStateCatalog
    unresolved: tuple[str, ...] = ()

    @property
    def denominator_proven(self) -> bool:
        expected = len(self.weight_catalog.states) * len(self.trait_glyph_catalog.states)
        return bool(
            self.weight_catalog.denominator_proven
            and self.trait_glyph_catalog.denominator_proven
            and expected > 0
            and len(self.states) == expected
            and not self.unresolved
        )


class ExtremeArmorResourceWeightTraitGlyphStateService:
    """Cross reviewed resource armor weight and joint trait/glyph witnesses."""

    SUPPORTED_OBJECTIVES = ExtremeArmorResourceTraitGlyphStateService.SUPPORTED_OBJECTIVES

    def __init__(
        self,
        *,
        weight_catalog: ExtremeArmorResourceWeightStateCatalog,
        trait_glyph_catalog: ExtremeArmorResourceTraitGlyphStateCatalog,
    ) -> None:
        self.weight_catalog = weight_catalog
        self.trait_glyph_catalog = trait_glyph_catalog

    @classmethod
    def from_services(
        cls,
        objective_key: str,
        *,
        trait_glyph_service: ExtremeArmorResourceTraitGlyphStateService,
    ) -> "ExtremeArmorResourceWeightTraitGlyphStateService":
        key = str(objective_key or "").strip().casefold()
        return cls(
            weight_catalog=ExtremeArmorResourceWeightStateService.build(key),
            trait_glyph_catalog=trait_glyph_service.build(key),
        )

    def build(self, objective_key: str) -> ExtremeArmorResourceWeightTraitGlyphStateCatalog:
        key = str(objective_key or "").strip().casefold()
        if key not in self.SUPPORTED_OBJECTIVES:
            raise KeyError(
                f"unreviewed Extreme resource armor weight/trait/glyph objective: {objective_key!r}"
            )
        if self.weight_catalog.objective_key != key:
            raise ValueError(
                "Extreme resource armor-weight catalog objective mismatch: "
                f"catalog={self.weight_catalog.objective_key!r}, requested={key!r}"
            )
        if self.trait_glyph_catalog.objective_key != key:
            raise ValueError(
                "Extreme resource armor trait/glyph catalog objective mismatch: "
                f"catalog={self.trait_glyph_catalog.objective_key!r}, requested={key!r}"
            )

        unresolved = tuple(
            dict.fromkeys(
                str(item)
                for item in (
                    *self.weight_catalog.unresolved,
                    *self.trait_glyph_catalog.unresolved,
                )
                if str(item)
            )
        )
        states = tuple(
            sorted(
                (
                    ExtremeArmorResourceWeightTraitGlyphState(
                        objective_key=key,
                        weight_state=weight_state,
                        trait_glyph_state=trait_glyph_state,
                    )
                    for weight_state in self.weight_catalog.states
                    for trait_glyph_state in self.trait_glyph_catalog.states
                ),
                key=lambda row: row.identity,
            )
        )
        if not states:
            unresolved = tuple(
                dict.fromkeys(
                    (
                        *unresolved,
                        f"No combined resource armor weight/trait/glyph states were produced for {key}",
                    )
                )
            )

        return ExtremeArmorResourceWeightTraitGlyphStateCatalog(
            objective_key=key,
            states=states,
            weight_catalog=self.weight_catalog,
            trait_glyph_catalog=self.trait_glyph_catalog,
            unresolved=unresolved,
        )

    @staticmethod
    def materialize(
        build: PlayerBuild,
        state: ExtremeArmorResourceWeightTraitGlyphState,
    ) -> PlayerBuild:
        candidate = ExtremeArmorResourceTraitGlyphStateService.materialize(
            build,
            state.trait_glyph_state,
        )
        return ExtremeArmorResourceWeightStateService.materialize(
            candidate,
            state.weight_state,
        )
