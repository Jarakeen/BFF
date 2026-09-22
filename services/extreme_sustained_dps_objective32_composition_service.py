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
        mundus_food_adapter: object | None = None,
        encounter_policy_adapter: object | None = None,
        finalized_potion_adapter: object | None = None,
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
        if rotation_adapter is None or runtime_policy_adapter is None:
            raise ValueError(
                "Objective #32 composition requires generated rotation and runtime-policy adapters"
            )
        if runtime_evaluation is None:
            raise ValueError(
                "Objective #32 composition requires canonical generated runtime evaluation"
            )
        if finalized_potion_evidence_resolver is None:
            raise ValueError(
                "Objective #32 composition requires finalized potion timing evidence"
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
        )

        return ExtremeSustainedDPSObjective32Composition(
            pipeline=pipeline,
            global_search=global_search,
            objective32=objective32,
            evidence=(
                "Objective #32 production graph composed from canonical generated frontier authorities",
                "Finalized potion timing is appended after runtime-policy axes",
                "Exact leaves use canonical generated runtime evaluation",
                "Additional potion resource-event denominator is explicitly proven complete",
            ),
        )


__all__ = [
    "ExtremeSustainedDPSObjective32Composition",
    "ExtremeSustainedDPSObjective32CompositionService",
]
