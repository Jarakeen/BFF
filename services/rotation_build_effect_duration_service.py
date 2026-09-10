from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from engine.config import DEFAULT_DATABASE
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_availability import resolve_available_effects
from minmax.character_build.effect_duration_resolver import (
    EffectDurationResolution,
    EffectDurationResolver,
)
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId
from minmax.character_build.passive_grant import PassiveGrant
from minmax.character_build.support_effect_resolver import equipped_gear_set_counts
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.gear_set_repository import GearSetRepository


class RotationBuildEffectDurationService:
    """Resolve one rotation-relevant effect duration from the actual build.

    This service is deliberately a thin composition boundary. Character-build
    effect availability decides which skill/CP/passive effects are mechanically
    present on the requested bar. Equipped canonical gear-set identities are then
    resolved through the existing verified gear-set EffectVariant bridge so saved
    builds do not need duration-modifier effects duplicated onto every gear piece.
    EffectDurationResolver applies only verified duration semantics. Rotation policy
    receives the resolved answer and never parses item or passive tooltip text itself.
    """

    def __init__(
        self,
        resolver: EffectDurationResolver | None = None,
        *,
        database_path: str | Path = DEFAULT_DATABASE,
        gear_set_effect_resolver: GearSetEffectVariantResolver | None = None,
    ) -> None:
        self.resolver = resolver or EffectDurationResolver()
        self.database_path = Path(database_path)
        self.gear_set_effect_resolver = (
            gear_set_effect_resolver
            or GearSetEffectVariantResolver(GearSetRepository(self.database_path))
        )

    def resolve(
        self,
        *,
        build: CharacterBuild,
        active_bar: BarId,
        effect: EffectVariant,
        passives: Iterable[PassiveGrant] = (),
    ) -> EffectDurationResolution:
        available_effects = list(
            resolve_available_effects(
                build,
                active_bar,
                tuple(passives),
            )
        )
        seen = {self._effect_key(candidate) for candidate in available_effects}
        for set_id, piece_count in equipped_gear_set_counts(
            build,
            active_bar=active_bar,
        ).items():
            try:
                numeric_set_id = int(set_id)
            except (TypeError, ValueError):
                continue
            for candidate in self.gear_set_effect_resolver.resolve(
                numeric_set_id,
                piece_count,
            ):
                key = self._effect_key(candidate)
                if key in seen:
                    continue
                seen.add(key)
                available_effects.append(candidate)
        return self.resolver.resolve(
            effect,
            available_effects=tuple(available_effects),
        )

    @staticmethod
    def _effect_key(effect: EffectVariant) -> tuple[object, ...]:
        return (
            effect.name.casefold(),
            effect.layer,
            effect.source.casefold(),
            effect.magnitude,
            effect.duration,
            effect.chance,
            effect.cooldown,
            effect.target_count,
            effect.range,
            effect.scaling,
            effect.condition,
            effect.target,
            effect.active_bar,
            effect.trigger,
            effect.target_type,
            effect.category,
            effect.stacking,
            effect.exclusivity_group,
            effect.eligible,
        )


__all__ = ["RotationBuildEffectDurationService"]
