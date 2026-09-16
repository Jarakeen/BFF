from __future__ import annotations

"""Extreme-only bridge from proven runtime conditions into canonical gear math.

Normal saved-build calculations remain unchanged. Extreme callers may provide an
explicit, proof-owned set of canonical condition markers; the shared gear resolver
then suppresses conditional set effects whose marker is absent and activates only
those whose marker is present. Reviewed named-buff witnesses are translated into
canonical CombatState snapshots so normal named-buff deduplication still applies.
"""

from dataclasses import replace

from minmax.combat_state import CombatState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.derived_stats import StatContribution
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_set_healing_condition_resolver import GearSetHealingConditionResolver
from minmax.gear_set_resource_condition_resolver import GearSetResourceConditionResolver
from minmax.gear_stat_inputs import (
    CORE_FIELDS,
    RESOURCE_STATS,
    GearCalculationInputs,
    GearStatInputResolver,
)
from minmax.phase5_context_factory import Phase5BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_actual_heal_gear_precondition_effect_resolver import (
    ExtremeActualHealGearPreconditionEffectResolver,
)
from services.extreme_actual_heal_gear_precondition_witness_service import (
    CLAW_OF_YOLNAHKRIIN_MINOR_COURAGE_CONDITION,
    CRUSADER_MINOR_COURAGE_CONDITION,
    FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION,
    NAGA_SHAMAN_MINOR_MENDING_CONDITION,
    NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION,
    PHOENIX_MOTH_MINOR_COURAGE_CONDITION,
    SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION,
    VESTMENT_OF_OLORIME_MAJOR_COURAGE_CONDITION,
)
from services.extreme_gear_set_power_tradeoff_resolver import (
    ExtremeGearSetPowerTradeoffResolver,
)
from services.extreme_resource_canonical_static_snapshot_service import (
    ExtremeResourceCanonicalStaticSnapshotService,
)


class _ExtremeConditionedGearEffectResolver:
    """Shared static grammar plus reviewed Extreme conditional/tradeoff grammar."""

    def __init__(self) -> None:
        self.static = GearSetEffectResolver()
        self.resource_conditions = GearSetResourceConditionResolver()
        self.healing_conditions = GearSetHealingConditionResolver()
        self.power_tradeoffs = ExtremeGearSetPowerTradeoffResolver()
        self.precondition_effects = ExtremeActualHealGearPreconditionEffectResolver()

    def resolve(self, bonus, *, use_max_value=True, source=None):
        for resolver in (
            self.static,
            self.resource_conditions,
            self.healing_conditions,
            self.power_tradeoffs,
            self.precondition_effects,
        ):
            effects = resolver.resolve(
                bonus,
                use_max_value=use_max_value,
                source=source,
            )
            if effects:
                return effects
        return []


class ExtremeResourceConditionedGearStatInputResolver(GearStatInputResolver):
    """Apply shared gear math with an explicit canonical condition context."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.service.resolver = _ExtremeConditionedGearEffectResolver()

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
        gear_set_repository = kwargs.get("gear_set_repository")
        database_path = getattr(gear_set_repository, "database_path", None)
        if database_path is not None:
            preload = getattr(gear_set_repository, "preload_all_static", None)
            if callable(preload):
                preload()
            snapshot = ExtremeResourceCanonicalStaticSnapshotService(database_path).build()
            kwargs.setdefault("armor_glyph_repository", snapshot.armor_glyph_repository)
            kwargs.setdefault("jewelry_glyph_repository", snapshot.jewelry_glyph_repository)
            kwargs.setdefault("jewelry_trait_repository", snapshot.jewelry_trait_repository)
            kwargs.setdefault("skill_line_repository", snapshot.skill_line_repository)
            kwargs.setdefault("racial_passive_repository", snapshot.racial_passive_repository)

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

    @staticmethod
    def _combat_state_with_reviewed_gear_witnesses(
        combat_state: CombatState,
        condition_context: frozenset[str] | None,
    ) -> CombatState:
        active = condition_context or frozenset()
        buffs = list(combat_state.active_buffs)
        if {
            CLAW_OF_YOLNAHKRIIN_MINOR_COURAGE_CONDITION,
            CRUSADER_MINOR_COURAGE_CONDITION,
            FLEDGLINGS_NEST_MINOR_COURAGE_CONDITION,
            PHOENIX_MOTH_MINOR_COURAGE_CONDITION,
        } & active:
            buffs.append("Minor Courage")
        if {
            NIX_HOUNDS_HOWL_MAJOR_COURAGE_CONDITION,
            SPELL_POWER_CURE_MAJOR_COURAGE_CONDITION,
            VESTMENT_OF_OLORIME_MAJOR_COURAGE_CONDITION,
        } & active:
            buffs.append("Major Courage")
        if NAGA_SHAMAN_MINOR_MENDING_CONDITION in active:
            buffs.append("Minor Mending")
        if tuple(buffs) == combat_state.active_buffs:
            return combat_state
        return replace(
            combat_state,
            in_combat=True,
            active_buffs=tuple(buffs),
        )

    def build(
        self,
        *,
        gear_condition_context: frozenset[str] | None = None,
        **kwargs,
    ):
        previous = self._extreme_gear_condition_context
        self._extreme_gear_condition_context = gear_condition_context
        base_combat_state = kwargs.get("combat_state", CombatState())
        kwargs["combat_state"] = self._combat_state_with_reviewed_gear_witnesses(
            base_combat_state,
            gear_condition_context,
        )
        try:
            return super().build(**kwargs)
        finally:
            self._extreme_gear_condition_context = previous

    def gear_inputs_with_condition(
        self,
        build: PlayerBuild,
        *,
        progression,
        active_bar: str,
        combat_state,
        incoming_attack,
        condition_context: frozenset[str] | None,
    ) -> GearCalculationInputs:
        previous = self._extreme_gear_condition_context
        self._extreme_gear_condition_context = condition_context
        reviewed_combat_state = self._combat_state_with_reviewed_gear_witnesses(
            combat_state,
            condition_context,
        )
        try:
            return self._gear_inputs(
                build,
                progression=progression,
                active_bar=active_bar,
                combat_state=reviewed_combat_state,
                incoming_attack=incoming_attack,
            )
        finally:
            self._extreme_gear_condition_context = previous

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
