from __future__ import annotations

"""Extreme-only bridge from proven runtime conditions into canonical gear math.

Normal saved-build calculations remain unchanged.  Extreme callers may provide an
explicit, proof-owned set of canonical condition markers; the shared gear resolver
then suppresses conditional set effects whose marker is absent and activates only
those whose marker is present.
"""

from dataclasses import replace

from minmax.context_factory import BuildCalculationContextFactory
from minmax.derived_stats import StatContribution
from minmax.gear_stat_inputs import (
    CORE_FIELDS,
    RESOURCE_STATS,
    GearCalculationInputs,
    GearStatInputResolver,
)
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild


class ExtremeResourceConditionedGearStatInputResolver(GearStatInputResolver):
    """Apply shared gear math with an explicit canonical condition context."""

    def resolve(
        self,
        build: PlayerBuild,
        *,
        active_bar: str = "front",
        condition_context: frozenset[str] | None = None,
    ) -> GearCalculationInputs:
        counts = self.equipped_set_counts(build, active_bar=active_bar)
        result = GearCalculationInputs(set_counts=tuple(sorted(counts.items())))

        for effect in self.service.active_static_effects(
            counts,
            condition_context=condition_context,
        ):
            if effect.stat is None:
                continue
            if effect.stat is StatId.CRITICAL_CHANCE:
                ratio = self.critical_rating_to_ratio(effect.value)
                contribution = StatContribution(effect.source, ratio)
                core = result.core
                weapon_critical = replace(
                    core.weapon_critical,
                    additive_after_percent=core.weapon_critical.additive_after_percent
                    + (contribution,),
                )
                spell_critical = replace(
                    core.spell_critical,
                    additive_after_percent=core.spell_critical.additive_after_percent
                    + (contribution,),
                )
                result = replace(
                    result,
                    core=replace(
                        core,
                        weapon_critical=weapon_critical,
                        spell_critical=spell_critical,
                    ),
                    applied_effect_count=result.applied_effect_count + 2,
                )
                continue

            resource_field = RESOURCE_STATS.get(effect.stat)
            if resource_field:
                before = getattr(result, resource_field)
                updated = self._resource_add(before, effect)
                if updated != before:
                    result = replace(
                        result,
                        **{
                            resource_field: updated,
                            "applied_effect_count": result.applied_effect_count + 1,
                        },
                    )
                continue

            if effect.stat in CORE_FIELDS:
                updated_core = self._core_add(result.core, effect.stat, effect)
                if updated_core != result.core:
                    result = replace(
                        result,
                        core=updated_core,
                        applied_effect_count=result.applied_effect_count + 1,
                    )

        result = self._apply_armor_glyphs(result, build)
        result = self._apply_jewelry_traits(result, build)
        result = self._apply_jewelry_glyphs(result, build)
        return result


class ExtremeResourceConditionedPhase5ContextFactory(Phase5BuildCalculationContextFactory):
    """Phase 5 context factory carrying one explicit Extreme gear-condition state."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        existing = self.gear_resolver
        if existing is not None and not isinstance(
            existing,
            ExtremeResourceConditionedGearStatInputResolver,
        ):
            self.gear_resolver = ExtremeResourceConditionedGearStatInputResolver(
                existing.repository,
                armor_glyph_repository=existing.armor_glyph_repository,
                jewelry_glyph_repository=existing.jewelry_glyph_repository,
                jewelry_trait_repository=existing.jewelry_trait_repository,
            )
        self._extreme_gear_condition_context: frozenset[str] | None = None

    def build(
        self,
        *,
        gear_condition_context: frozenset[str] | None = None,
        **kwargs,
    ):
        self._extreme_gear_condition_context = gear_condition_context
        try:
            return super().build(**kwargs)
        finally:
            self._extreme_gear_condition_context = None

    def _resolved_gear_inputs(
        self,
        build: PlayerBuild,
        *,
        active_bar: str,
    ) -> GearCalculationInputs:
        if self.gear_resolver is None:
            return GearCalculationInputs()

        condition_context = self._extreme_gear_condition_context
        cache_key = (
            *BuildCalculationContextFactory._gear_resolution_cache_key(build, active_bar),
            None
            if condition_context is None
            else tuple(sorted(condition_context, key=str.casefold)),
        )
        cached = self._gear_resolution_cache.get(cache_key)
        if cached is not None:
            return cached

        if isinstance(self.gear_resolver, ExtremeResourceConditionedGearStatInputResolver):
            resolved = self.gear_resolver.resolve(
                build,
                active_bar=active_bar,
                condition_context=condition_context,
            )
        else:
            resolved = self.gear_resolver.resolve(build, active_bar=active_bar)
        self._gear_resolution_cache[cache_key] = resolved
        return resolved


__all__ = [
    "ExtremeResourceConditionedGearStatInputResolver",
    "ExtremeResourceConditionedPhase5ContextFactory",
]
