from __future__ import annotations

"""Canonical composition root for generated Objective #32 sustained-DPS search."""

from dataclasses import dataclass

from services.extreme_sustained_dps_generated_axis_pipeline_leaf_evaluation_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService,
)
from services.extreme_sustained_dps_generated_axis_pipeline_service import (
    ExtremeSustainedDPSGeneratedAxisPipelineService,
)
from services.extreme_sustained_dps_generated_finalized_potion_axis_adapter_service import (
    ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService,
)
from services.extreme_sustained_dps_global_generated_search_service import (
    ExtremeSustainedDPSGlobalGeneratedSearchService,
)
from services.extreme_sustained_dps_global_objective32_search_service import (
    ExtremeSustainedDPSGlobalObjective32SearchService,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSObjective32Composition:
    pipeline: ExtremeSustainedDPSGeneratedAxisPipelineService
    global_search: ExtremeSustainedDPSGlobalGeneratedSearchService
    objective32: ExtremeSustainedDPSGlobalObjective32SearchService
    evidence: tuple[str, ...]


class ExtremeSustainedDPSObjective32CompositionService:
    """Assemble the canonical generated Objective #32 service graph.

    Low-level frontier construction remains owned by the existing canonical services.
    This composition root wires those already-configured authorities into the exact
    production graph searched by Objective #32 and enforces proof-critical late-stage
    potion timing ownership.
    """

    @staticmethod
    def _require_resource_denominator_proof(
        finalized_potion_evidence_resolver: object,
    ) -> None:
        proven = bool(
            getattr(
                finalized_potion_evidence_resolver,
                "additional_resource_event_denominator_proven",
                False,
            )
        )
        if not proven:
            raise ValueError(
                "Objective #32 composition requires finalized potion timing evidence "
                "with a proven-complete additional resource-event denominator"
            )

    @classmethod
    def compose(
        cls,
        *,
        structural_families: object,
        structural_materialization: object,
        gear_adapter: object,
        late_adapter: object,
        rotation_adapter: object,
        runtime_policy_adapter: object,
        runtime_evaluation: object,
        finalized_potion_evidence_resolver: object,
        runtime_state_frontier_resolver: object,
        mundus_food_adapter: object,
        encounter_policy_adapter: object,
        finalized_potion_adapter: object | None = None,
        potion_cooldown_resolver: object | None = None,
    ) -> ExtremeSustainedDPSObjective32Composition:
        if structural_families is None:
            raise ValueError("Objective #32 composition requires structural families")
        if structural_materialization is None:
            raise ValueError(
                "Objective #32 composition requires structural materialization"
            )
        if gear_adapter is None or late_adapter is None:
            raise ValueError(
                "Objective #32 composition requires generated gear and late adapters"
            )
        if mundus_food_adapter is None:
            raise ValueError(
                "Objective #32 composition requires canonical Mundus/food adapter"
            )
        if encounter_policy_adapter is None:
            raise ValueError(
                "Objective #32 composition requires canonical encounter-policy adapter"
            )
        if rotation_adapter is None or runtime_policy_adapter is None:
            raise ValueError(
                "Objective #32 composition requires generated rotation and runtime-policy adapters"
            )
        if runtime_evaluation is None:
            raise ValueError(
                "Objective #32 composition requires canonical generated runtime evaluation"
            )
        if not bool(
            getattr(
                runtime_policy_adapter,
                "require_complete_heavy_attack_discovery",
                False,
            )
        ):
            raise ValueError(
                "Objective #32 composition requires runtime-policy adapter complete Heavy Attack discovery mode"
            )
        if finalized_potion_evidence_resolver is None:
            raise ValueError(
                "Objective #32 composition requires finalized potion timing evidence"
            )
        if runtime_state_frontier_resolver is None:
            raise ValueError(
                "Objective #32 composition requires candidate-resolved runtime-state authority"
            )
        scenario_frontier = getattr(
            runtime_state_frontier_resolver,
            "scenario_frontier",
            None,
        )
        if scenario_frontier is None:
            raise ValueError(
                "Objective #32 composition requires runtime-state authority backed by the canonical scenario frontier"
            )
        if getattr(scenario_frontier, "runtime_effect_universe", None) is None:
            raise ValueError(
                "Objective #32 composition requires canonical candidate runtime EffectVariant discovery"
            )
        if getattr(scenario_frontier, "runtime_effect_scaling", None) is None:
            raise ValueError(
                "Objective #32 composition requires canonical candidate runtime effect scaling"
            )
        runtime_effect_universe = getattr(
            scenario_frontier,
            "runtime_effect_universe",
            None,
        )
        if getattr(
            runtime_effect_universe,
            "weapon_enchantment_runtime_source_service",
            None,
        ) is None or getattr(
            runtime_effect_universe,
            "weapon_enchantment_runtime_variant_service",
            None,
        ) is None:
            raise ValueError(
                "Objective #32 composition requires dedicated canonical weapon-enchantment runtime source and variant projection"
            )
        if getattr(
            scenario_frontier,
            "weapon_enchantment_activation_service",
            None,
        ) is None:
            raise ValueError(
                "Objective #32 composition requires canonical weapon-enchantment activation-event resolution"
            )
        if getattr(
            scenario_frontier,
            "weapon_enchantment_cooldown_policy_resolver",
            None,
        ) is None:
            raise ValueError(
                "Objective #32 composition requires canonical weapon-enchantment cooldown-policy authority"
            )
        if not bool(
            getattr(
                runtime_state_frontier_resolver,
                "supplemental_event_denominator_proven",
                False,
            )
        ):
            raise ValueError(
                "Objective #32 composition requires a proven-complete supplemental runtime-event denominator"
            )
        if not bool(
            getattr(
                runtime_state_frontier_resolver,
                "supplemental_history_denominator_proven",
                False,
            )
        ):
            raise ValueError(
                "Objective #32 composition requires a proven-complete supplemental runtime-history denominator"
            )

        cls._require_resource_denominator_proof(
            finalized_potion_evidence_resolver
        )

        potion_adapter = (
            finalized_potion_adapter
            or ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService()
        )

        pipeline = ExtremeSustainedDPSGeneratedAxisPipelineService(
            gear_adapter=gear_adapter,
            mundus_food_adapter=mundus_food_adapter,
            late_adapter=late_adapter,
            encounter_policy_adapter=encounter_policy_adapter,
            rotation_adapter=rotation_adapter,
            runtime_policy_adapter=runtime_policy_adapter,
            finalized_potion_adapter=potion_adapter,
            finalized_potion_evidence_resolver=(
                finalized_potion_evidence_resolver
            ),
            runtime_state_frontier_resolver=runtime_state_frontier_resolver,
        )
        leaf_evaluation = (
            ExtremeSustainedDPSGeneratedAxisPipelineLeafEvaluationService(
                runtime_evaluation=runtime_evaluation,
            )
        )
        global_search = ExtremeSustainedDPSGlobalGeneratedSearchService(
            structural_families=structural_families,
            structural_materialization=structural_materialization,
            pipeline=pipeline,
            leaf_evaluation=leaf_evaluation,
        )
        objective32 = ExtremeSustainedDPSGlobalObjective32SearchService(
            global_search=global_search,
            structural_families=structural_families,
            require_closure_ready_scenario=True,
            potion_cooldown_resolver=potion_cooldown_resolver,
        )

        return ExtremeSustainedDPSObjective32Composition(
            pipeline=pipeline,
            global_search=global_search,
            objective32=objective32,
            evidence=(
                "Objective #32 production graph composed from canonical generated frontier authorities",
                "Mundus/food and encounter-policy canonical axes are required by composition",
                "Finalized potion timing is appended after runtime-policy axes",
                "Heavy Attack timing uses scheduler-derived complete-discovery mode",
                "Exact leaves use canonical generated runtime evaluation",
                "Additional potion resource-event denominator is explicitly proven complete",
                "Effective potion cooldown is resolved from each finalized build through the canonical fail-closed cooldown authority",
                "Runtime state is resolved per finalized candidate inside the generated tree",
                "Candidate runtime state is backed by canonical EffectVariant discovery and candidate-specific scaling",
                "Canonical weapon-enchantment source projection, activation events, and cooldown-policy authority are required in the production runtime-state graph",
                "Supplemental runtime-event and runtime-history denominators are proven complete before global traversal",
                "Canonical Objective #32 search requires closure-ready Heavy Attack channel-block scenario evidence before traversal",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSObjective32Composition",
    "ExtremeSustainedDPSObjective32CompositionService",
]
