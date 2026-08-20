from __future__ import annotations

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
    ):
        self.gear_set_effect_service = gear_set_effect_service
        self.race_effect_service = race_effect_service

    def resolve_effects(self, build: Build) -> list[Effect]:
        """Resolve all currently supported effects for a build."""

        effects: list[Effect] = []

        # Preserve effects explicitly attached to the build.
        effects.extend(build.effects)

        # Resolve racial stat effects.
        if (
            build.race_id is not None
            and self.race_effect_service is not None
        ):
            effects.extend(
                self.race_effect_service.resolve_effects(
                    build.race_id,
                )
            )

        # Resolve effects contributed by equipped gear sets.
        for gear_set in build.gear_sets:
            effects.extend(
                self.gear_set_effect_service.resolve_effects(
                    gear_set.set_id,
                    gear_set.piece_count,
                )
            )

        return effects