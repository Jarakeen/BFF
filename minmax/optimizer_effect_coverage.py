from __future__ import annotations

from collections.abc import Iterable

from .character_build.character_build import CharacterBuild
from .character_build.effect_instance import EffectVariant
from .character_build.effect_layer import BarId
from .character_build.passive_grant import PassiveGrant
from .character_build.support_effect_resolver import CharacterBuildSupportEffectResolver
from .effect_coverage import EffectCoverageReport, analyze_effect_coverage
from .character_build.effect_relationship import ConditionContext, EffectRelationship


def resolve_build_effect_variants(
    build: CharacterBuild,
    resolver: CharacterBuildSupportEffectResolver,
    *,
    passives: Iterable[PassiveGrant] = (),
    relationships: Iterable[EffectRelationship] = (),
    condition_context: ConditionContext | None = None,
) -> tuple[EffectVariant, ...]:
    """Resolve the build's effects across both bars for optimizer analysis.

    Coverage is a build-level question rather than an active-bar question,
    so both bars are considered. Effects that are identical evidence from
    the same provider on both bars are collapsed; distinct providers remain
    distinct so redundancy can be detected and explained.

    Ultimate effects without a runtime trigger are included. Triggered
    ultimate effects remain available to the existing resolver but are not
    assumed to be active without a supplied trigger context.
    """
    resolved: list[EffectVariant] = []
    for bar in build.bars():
        resolved.extend(
            _resolver_variants(
                build,
                resolver,
                bar.bar_id,
                passives=passives,
                relationships=relationships,
                condition_context=condition_context,
            )
        )

    unique: dict[tuple[object, ...], EffectVariant] = {}
    for effect in resolved:
        key = (
            effect.name,
            effect.source,
            effect.layer,
            effect.magnitude,
            effect.duration,
            effect.chance,
            effect.cooldown,
            effect.target_count,
            effect.range,
            effect.scaling,
            effect.condition,
            effect.active_bar,
            effect.trigger,
            effect.target_type,
            effect.category,
            effect.stacking,
            effect.exclusivity_group,
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
    variants = resolve_build_effect_variants(
        build,
        resolver,
        passives=passives,
        relationships=relationships,
        condition_context=condition_context,
    )

    # Reuse the established conversion path so this report is based on the
    # same EffectVariant -> SupportEffect semantics as the rest of minmax.
    from .character_build.support_effect_resolver import effect_variant_to_support_effect

    support_effects = tuple(
        effect_variant_to_support_effect(effect)
        for effect in variants
        if effect.eligible
    )
    return analyze_effect_coverage(support_effects)


def _resolver_variants(
    build: CharacterBuild,
    resolver: CharacterBuildSupportEffectResolver,
    bar: BarId,
    *,
    passives: Iterable[PassiveGrant],
    relationships: Iterable[EffectRelationship],
    condition_context: ConditionContext | None,
) -> tuple[EffectVariant, ...]:
    """Keep the resolver call in one place so coverage has one source of truth."""
    return _variants_from_registry(
        resolver.resolve(
            build,
            bar,
            passives=passives,
            relationships=relationships,
            condition_context=condition_context,
        )
    )


def _variants_from_registry(registry) -> tuple[EffectVariant, ...]:
    """Convert the established registry representation back to effect evidence.

    The current CharacterBuildSupportEffectResolver exposes SupportEffectRegistry,
    so this helper intentionally preserves its public fields rather than
    reaching into private resolver state. This is a compatibility bridge until
    the resolver itself exposes a native EffectVariant result API.
    """
    from .character_build.effect_instance import EffectVariant
    from .character_build.effect_layer import EffectLayer

    variants: list[EffectVariant] = []
    for effect in registry.all():
        variants.append(
            EffectVariant(
                name=effect.name,
                layer=EffectLayer.SLOTTED,
                source=effect.source,
                magnitude=effect.magnitude,
                duration=effect.duration,
                target_count=effect.target_count,
                range=effect.range,
                scaling=effect.scaling,
                condition=effect.conditions[0] if effect.conditions else None,
                target_type=effect.target_type,
                category=effect.category,
                stacking=effect.stacking,
                exclusivity_group=effect.exclusivity_group,
                trigger=effect.trigger.trigger if effect.trigger else None,
                eligible=True,
            )
        )
    return tuple(variants)
