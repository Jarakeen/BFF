from __future__ import annotations

from collections.abc import Iterable

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.effect_availability import resolve_available_effects
from minmax.character_build.effect_duration_resolver import (
    EffectDurationResolution,
    EffectDurationResolver,
)
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import BarId
from minmax.character_build.passive_grant import PassiveGrant


class RotationBuildEffectDurationService:
    """Resolve one rotation-relevant effect duration from the actual build.

    This service is deliberately a thin composition boundary. Character-build
    effect availability decides which gear/CP/passive effects are mechanically
    present on the requested bar. EffectDurationResolver then applies only
    verified duration-modifier semantics. Rotation policy receives the resolved
    answer and never parses item or passive tooltip text itself.
    """

    def __init__(self, resolver: EffectDurationResolver | None = None) -> None:
        self.resolver = resolver or EffectDurationResolver()

    def resolve(
        self,
        *,
        build: CharacterBuild,
        active_bar: BarId,
        effect: EffectVariant,
        passives: Iterable[PassiveGrant] = (),
    ) -> EffectDurationResolution:
        available_effects = resolve_available_effects(
            build,
            active_bar,
            tuple(passives),
        )
        return self.resolver.resolve(
            effect,
            available_effects=available_effects,
        )


__all__ = ["RotationBuildEffectDurationService"]
