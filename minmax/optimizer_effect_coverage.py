from __future__ import annotations

from collections.abc import Iterable

from .character_build.character_build import CharacterBuild
from .character_build.effect_relationship import ConditionContext, EffectRelationship
from .character_build.passive_grant import PassiveGrant
from .character_build.support_effect_resolver import CharacterBuildSupportEffectResolver
from .effect_coverage import EffectCoverageReport, analyze_effect_coverage
from .support_effect import SupportEffect


def resolve_build_support_effects(
    build: CharacterBuild,
    resolver: CharacterBuildSupportEffectResolver,
    *,
    passives: Iterable[PassiveGrant] = (),
    relationships: Iterable[EffectRelationship] = (),
    condition_context: ConditionContext | None = None,
) -> tuple[SupportEffect, ...]:
    """Resolve the build's support effects across both bars.

    Coverage is a build-level question, so both bars are considered. The
    established CharacterBuildSupportEffectResolver remains the source of
    truth for skill, ultimate, passive, gear, and weapon effect resolution.
    """
    resolved: list[SupportEffect] = []
    for bar in build.bars():
        resolved.extend(
            resolver.resolve(
                build,
                bar.bar_id,
                passives=passives,
                relationships=relationships,
                condition_context=condition_context,
            ).all()
        )

    # The same gear/passive effect can legitimately be encountered while
    # resolving both bars. Collapse only exact same-provider evidence; keep
    # different sources distinct so redundancy remains visible.
    unique: dict[tuple[object, ...], SupportEffect] = {}
    for effect in resolved:
        key = (
            effect.name.casefold(),
            effect.source,
            effect.category,
            effect.effect_type,
            effect.target_type,
            effect.magnitude,
            effect.unit,
            effect.target_count,
            effect.range,
            effect.duration,
            effect.scaling,
            effect.stacking,
            effect.exclusivity_group,
            effect.conditions,
            repr(effect.trigger),
            effect.damage_amplification,
            effect.resistance_reduction,
            effect.penetration,
            effect.resource_type,
            effect.resource_value,
            effect.applies_status,
            effect.requires_status,
        )
        unique.setdefault(key, effect)

    return tuple(unique.values())


def analyze_build_effect_coverage(
    build: CharacterBuild,
    resolver: CharacterBuildSupportEffectResolver,
    *,
    passives: Iterable[PassiveGrant] = (),
    relationships: Iterable[EffectRelationship] = (),
    condition_context: ConditionContext | None = None,
) -> EffectCoverageReport:
    """Produce the optimizer's normalized effect-coverage report."""
    return analyze_effect_coverage(
        resolve_build_support_effects(
            build,
            resolver,
            passives=passives,
            relationships=relationships,
            condition_context=condition_context,
        )
    )
