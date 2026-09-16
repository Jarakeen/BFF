from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation
from services.extreme_actual_heal_armor_weight_candidate_service import (
    ExtremeActualHealArmorWeightCandidateService,
)
from services.extreme_actual_heal_armor_weight_legality_service import (
    ExtremeActualHealArmorWeightLegalityService,
)
from services.extreme_actual_heal_armor_weight_package_adapter import (
    ExtremeActualHealArmorWeightPackageAdapter,
)
from services.extreme_actual_heal_attribute_projection_service import (
    ExtremeActualHealAttributeProjectionService,
)
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)
from services.extreme_actual_heal_candidate_gear_condition_service import (
    ExtremeActualHealCandidateGearConditionService,
)
from services.extreme_actual_heal_champion_point_candidate_service import (
    ExtremeActualHealChampionPointCandidateService,
)
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationService,
)
from services.extreme_canonical_healing_event_service import (
    ExtremeCanonicalHealingEventService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedPhase5ContextFactory,
)


class ExtremeCanonicalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Standing Actual Heal optimizer with canonical heal-event aggregation.

    ``ExtremeActualHealOptimizationService`` owns the mature whole-build search.
    This subtype changes its default healing-event evaluator so standing
    optimization uses the same reviewed recipient/time identity semantics as the
    conditional Extreme path, and adds E2 legal-character search seams.

    Champion Point legality is score-neutral here: candidate bars are materialized
    first and the ordinary whole-build healing evaluator decides which legal bar
    wins. Mixed flat/percent/critical CP values are never compared as if they
    shared a unit. Any heal-relevant CP coverage gap remains explicit unresolved
    evidence.

    The standing H1 attribute axis is proof-reduced here. The complete legal
    64-point simplex remains the denominator, but a selected heal is reduced to
    pure Magicka/Stamina endpoints only when every contributing HEAL coefficient
    is on the reviewed type-8, non-negative highest-resource path. If that proof
    fails, the inherited conservative candidate path remains active and the proof
    gap is carried as unresolved evidence.

    Armor-weight search uses canonical set-piece ``armor_type`` evidence. The
    current gear layout is searched directly, while armor-bearing gear package
    services are decorated so every package candidate is expanded through its own
    physically legal armor-weight frontier before canonical event scoring. Raw
    slot layouts are proof-reduced by Medium-piece count plus distinct armor-type
    count, preserving the reviewed Agility/Dexterity and Undaunted Mettle inputs.

    Standing gear conditions are explicit. Final H1 scoring uses the existing
    Extreme conditioned Phase 5 context with only build-owned condition markers
    proven from canonical provisioning type, active weapon type, explicit
    transformed form, or selected-heal scope identity. Trigger/proc/pet/dodge/
    standing-state conditions are never invented merely because they would improve
    the result.

    Explicitly injected optimizers, healing-event evaluators, CP candidate
    services, attribute projection services, armor candidate services, condition
    services, candidate-scope services, and conditioned context factories remain
    authoritative for focused tests and specialist callers.
    """

    CP_SEARCH_SCOPE = "legal heal-relevant Champion Point loadout search"
    CONDITION_SEARCH_SCOPE = (
        "standing H1 gear effects scored only under explicit build-owned or selected-heal condition evidence"
    )
    _ARMOR_PACKAGE_SERVICES = (
        ("gear_set_candidates", "ordinary-five-piece"),
        ("monster_packages", "five-plus-monster"),
        ("double_five_packages", "double-five"),
        ("mythic_packages", "ring-mythic-package"),
        ("non_ring_mythic_packages", "non-ring-mythic-package"),
    )

    def __init__(
        self,
        *,
        optimizer: ExtremeCompleteOptimizationService | None = None,
        healing_events=None,
        champion_point_candidates: ExtremeActualHealChampionPointCandidateService | None = None,
        attribute_projection: ExtremeActualHealAttributeProjectionService | None = None,
        armor_weight_candidates: ExtremeActualHealArmorWeightCandidateService | None = None,
        build_condition_context: ExtremeActualHealBuildConditionContextService | None = None,
        candidate_gear_conditions: ExtremeActualHealCandidateGearConditionService | None = None,
        conditioned_context_factory=None,
        **kwargs,
    ) -> None:
        core_optimizer = optimizer or ExtremeCompleteOptimizationService()
        canonical_events = healing_events or ExtremeCanonicalHealingEventService(
            database_path=core_optimizer.database_path
        )
        super().__init__(
            optimizer=core_optimizer,
            healing_events=canonical_events,
            **kwargs,
        )
        database_path = getattr(core_optimizer, "database_path", None)
        self.champion_point_candidates = (
            champion_point_candidates
            or (
                ExtremeActualHealChampionPointCandidateService(database_path)
                if database_path is not None
                else None
            )
        )
        self.attribute_projection = (
            attribute_projection
            or (
                ExtremeActualHealAttributeProjectionService(database_path)
                if database_path is not None
                else None
            )
        )
        self.armor_weight_candidates = armor_weight_candidates
        if self.armor_weight_candidates is None and database_path is not None:
            self.armor_weight_candidates = ExtremeActualHealArmorWeightCandidateService(
                ExtremeActualHealArmorWeightLegalityService(database_path)
            )

        self.build_condition_context = build_condition_context or (
            ExtremeActualHealBuildConditionContextService(database_path)
            if database_path is not None
            else None
        )
        self.candidate_gear_conditions = candidate_gear_conditions or (
            ExtremeActualHealCandidateGearConditionService(database_path)
            if database_path is not None
            else None
        )
        self.conditioned_context_factory = conditioned_context_factory
        if self.conditioned_context_factory is None and database_path is not None:
            required_repositories = (
                getattr(core_optimizer, "race_repository", None),
                getattr(core_optimizer, "gear_set_repository", None),
                getattr(core_optimizer, "mundus_repository", None),
                getattr(core_optimizer, "provisioning_repository", None),
            )
            if all(repository is not None for repository in required_repositories):
                self.conditioned_context_factory = ExtremeResourceConditionedPhase5ContextFactory(
                    race_repository=required_repositories[0],
                    gear_set_repository=required_repositories[1],
                    mundus_repository=required_repositories[2],
                    provisioning_repository=required_repositories[3],
                )

        self._armor_package_adapters: list[ExtremeActualHealArmorWeightPackageAdapter] = []
        if self.armor_weight_candidates is not None:
            for attribute, label in self._ARMOR_PACKAGE_SERVICES:
                delegate = getattr(self, attribute, None)
                if delegate is None or isinstance(
                    delegate, ExtremeActualHealArmorWeightPackageAdapter
                ):
                    continue
                adapter = ExtremeActualHealArmorWeightPackageAdapter(
                    delegate,
                    self.armor_weight_candidates,
                    label=label,
                )
                setattr(self, attribute, adapter)
                self._armor_package_adapters.append(adapter)

        self._champion_point_search_unresolved: tuple[str, ...] = ()
        self._attribute_search_unresolved: tuple[str, ...] = ()
        self._attribute_search_scope: tuple[str, ...] = ()
        self._attribute_search_entity_id = ""
        self._armor_weight_search_unresolved: tuple[str, ...] = ()
        self._armor_weight_search_scope: tuple[str, ...] = ()

    def optimize(self, baseline_build, entity_id: str, *args, **kwargs):
        self._champion_point_search_unresolved = ()
        self._attribute_search_unresolved = ()
        self._attribute_search_scope = ()
        self._attribute_search_entity_id = str(entity_id or "").strip()
        self._armor_weight_search_unresolved = ()
        self._armor_weight_search_scope = ()
        for adapter in self._armor_package_adapters:
            adapter.reset()

        result = super().optimize(baseline_build, entity_id, *args, **kwargs)

        package_unresolved: list[str] = []
        raw_packages = expanded_packages = raw_layouts = retained_signatures = 0
        for adapter in self._armor_package_adapters:
            stats = adapter.stats
            raw_packages += stats.raw_package_candidates
            expanded_packages += stats.expanded_candidates
            raw_layouts += stats.raw_weight_layouts_reviewed
            retained_signatures += stats.retained_weight_signatures
            package_unresolved.extend(stats.unresolved)
        self._armor_weight_search_unresolved = tuple(
            dict.fromkeys(
                (*self._armor_weight_search_unresolved, *package_unresolved)
            )
        )
        if raw_packages:
            package_scope = (
                "armor-bearing H1 gear package composition: "
                f"{raw_packages} raw package candidates expanded to {expanded_packages} "
                f"physically legal package+weight candidates after reviewing {raw_layouts} "
                f"slot-weight layouts and retaining {retained_signatures} H1 signatures",
            )
            self._armor_weight_search_scope = tuple(
                dict.fromkeys((*self._armor_weight_search_scope, *package_scope))
            )

        unresolved = tuple(
            dict.fromkeys(
                (
                    *result.unresolved,
                    *self._champion_point_search_unresolved,
                    *self._attribute_search_unresolved,
                    *self._armor_weight_search_unresolved,
                )
            )
        )
        search_scope = result.search_scope
        if self.CP_SEARCH_SCOPE not in search_scope:
            search_scope = (*search_scope, self.CP_SEARCH_SCOPE)
        if (
            self.conditioned_context_factory is not None
            and self.build_condition_context is not None
            and self.CONDITION_SEARCH_SCOPE not in search_scope
        ):
            search_scope = (*search_scope, self.CONDITION_SEARCH_SCOPE)
        for item in (*self._attribute_search_scope, *self._armor_weight_search_scope):
            if item not in search_scope:
                search_scope = (*search_scope, item)
        return replace(
            result,
            unresolved=unresolved,
            search_scope=search_scope,
        )

    def _evaluate(
        self,
        build,
        *,
        progression,
        character_id: str,
        build_id: str,
        entity_id: str,
        active_bar: str,
    ):
        if self.conditioned_context_factory is None or self.build_condition_context is None:
            return super()._evaluate(
                build,
                progression=progression,
                character_id=character_id,
                build_id=build_id,
                entity_id=entity_id,
                active_bar=active_bar,
            )

        condition_state = self.build_condition_context.resolve(
            build,
            active_bar=active_bar,
        )
        candidate_state = (
            self.candidate_gear_conditions.resolve(
                build,
                entity_id,
                active_bar=active_bar,
            )
            if self.candidate_gear_conditions is not None
            else None
        )
        condition_context = frozenset(
            {
                *condition_state.condition_context,
                *(
                    candidate_state.condition_context
                    if candidate_state is not None
                    else frozenset()
                ),
            }
        )
        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        context = self.conditioned_context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
            gear_condition_context=condition_context,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
        )
        unresolved = (
            *tuple(context.unresolved_gear_effects),
            *tuple(event.unresolved),
            *tuple(condition_state.unresolved),
            *(
                tuple(candidate_state.unresolved)
                if candidate_state is not None
                else ()
            ),
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))

    def _resource_attribute_candidates(
        self,
        baseline_build,
        *,
        character_id: str,
        baseline_build_id: str,
    ):
        if self.attribute_projection is None or not self._attribute_search_entity_id:
            return super()._resource_attribute_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )

        result = self.attribute_projection.build_candidates(
            baseline_build,
            entity_id=self._attribute_search_entity_id,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        )
        if not result.denominator_proven:
            self._attribute_search_unresolved = tuple(
                dict.fromkeys(
                    (*self._attribute_search_unresolved, *result.unresolved)
                )
            )
            return super()._resource_attribute_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )

        self._attribute_search_scope = tuple(
            dict.fromkeys((*self._attribute_search_scope, *result.search_scope))
        )
        return result.candidates

    def _additional_candidates(
        self,
        baseline_build,
        *,
        progression,
        character_id: str,
        baseline_build_id: str,
        entity_id: str,
        active_bar: str,
    ):
        inherited = list(
            super()._additional_candidates(
                baseline_build,
                progression=progression,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
                entity_id=entity_id,
                active_bar=active_bar,
            )
        )

        if self.champion_point_candidates is not None:
            cp_result = self.champion_point_candidates.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
            self._champion_point_search_unresolved = tuple(
                dict.fromkeys(
                    (
                        *self._champion_point_search_unresolved,
                        *cp_result.unresolved,
                    )
                )
            )
            inherited.extend(cp_result.candidates)

        if self.armor_weight_candidates is not None:
            armor_result = self.armor_weight_candidates.build_candidates(
                baseline_build,
                character_id=character_id,
                baseline_build_id=baseline_build_id,
            )
            self._armor_weight_search_unresolved = tuple(
                dict.fromkeys(
                    (
                        *self._armor_weight_search_unresolved,
                        *armor_result.unresolved,
                    )
                )
            )
            if armor_result.denominator_proven:
                scope = (
                    f"physical armor-weight search for current gear layout: "
                    f"{armor_result.raw_layout_count} legal slot layouts reduced to "
                    f"{armor_result.retained_signature_count} H1-relevant signatures",
                )
                self._armor_weight_search_scope = tuple(
                    dict.fromkeys((*self._armor_weight_search_scope, *scope))
                )
                inherited.extend(armor_result.candidates)

        return tuple(inherited)
