from __future__ import annotations

from .armor_glyph_repository import ArmorGlyphEffectRepository
from .build import Build
from .effects import Effect
from .gear_set_effect_service import GearSetEffectService
from .race_effect_service import RaceEffectService


class BuildEffectService:
    """Collect effects contributed by the current Build configuration."""

    def __init__(
        self,
        gear_set_effect_service: GearSetEffectService,
        race_effect_service: RaceEffectService | None = None,
        armor_glyph_repository: ArmorGlyphEffectRepository | None = None,
    ):
        self.gear_set_effect_service = gear_set_effect_service
        self.race_effect_service = race_effect_service
        self.armor_glyph_repository = armor_glyph_repository

    def resolve_effects(self, build: Build) -> list[Effect]:
        """Resolve all currently supported effects for a build."""

        effects: list[Effect] = []

        # Explicit effects
        effects.extend(build.effects)

        # Racial stat effects
        if (
            build.race_id is not None
            and self.race_effect_service is not None
        ):
            effects.extend(
                self.race_effect_service.resolve_effects(
                    build.race_id,
                )
            )

        # Equipped armor glyphs
        if self.armor_glyph_repository is not None:
            for glyph in build.armor_glyphs:
                effects.extend(
                    self.armor_glyph_repository.get_armor_glyph_effect(
                        glyph.item_id,
                    )
                )

        # Gear-set effects
        for gear_set in build.gear_sets:
            effects.extend(
                self.gear_set_effect_service.resolve_effects(
                    gear_set.set_id,
                    gear_set.piece_count,
                )
            )

        return effects