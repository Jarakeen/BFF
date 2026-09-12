from __future__ import annotations

"""Adapt the proven Max Health named-gear frontier to the legacy realization contract.

The structural record stack consumes ``ExtremeObjectiveNamedGearSetCatalogRealizationResult``.
Max Health now has a proof-reduced candidate search rather than raw exhaustive named
assignment enumeration. This adapter preserves that existing downstream contract while
keeping reduction provenance explicit and reusing the canonical dual-bar legality audit
before the frontier is exposed as a source denominator.
"""

from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_max_health_named_gear_candidate_search_service import (
    ExtremeMaxHealthNamedGearCandidateSearchResult,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationResult,
    ExtremeNamedGearSetTopologyRealizationResult,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)


class ExtremeMaxHealthNamedGearRealizationAdapterService:
    """Expose the exact reduced Max Health frontier through the existing gear contract."""

    @staticmethod
    def _identity(realization) -> tuple[object, ...]:
        return ExtremeDualBarGearStateCatalogService.realization_identity(realization)

    @classmethod
    def build(
        cls,
        *,
        search: ExtremeMaxHealthNamedGearCandidateSearchResult,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> ExtremeObjectiveNamedGearSetCatalogRealizationResult:
        if str(relevance.objective_key or "").strip().casefold() != "max_health":
            raise ValueError("Max Health named-gear realization adapter supports max_health only")

        source = tuple(search.candidate_realizations)
        dual_bar = ExtremeDualBarGearStateCatalogService.build(
            source,
            source_denominator_proven=bool(search.candidate_reduction_proven),
            unresolved=tuple(search.unresolved),
        )
        admissible = dual_bar.admissible_realizations(active_bar="front")
        source_ids = {cls._identity(row) for row in source}
        admissible_ids = {cls._identity(row) for row in admissible}

        unresolved: list[str] = list(search.unresolved)
        unresolved.extend(dual_bar.unresolved)
        if source_ids != admissible_ids:
            missing = len(source_ids - admissible_ids)
            extra = len(admissible_ids - source_ids)
            unresolved.append(
                "Reduced Max Health named-gear frontier changed under canonical dual-bar "
                f"admissibility (missing={missing}, extra={extra})"
            )

        by_signature: dict[str, list[object]] = {}
        for row in admissible:
            by_signature.setdefault(str(row.topology_signature), []).append(row)

        topology_rows: list[ExtremeNamedGearSetTopologyRealizationResult] = []
        for topology in topology_catalog.topologies:
            realizations = tuple(
                sorted(
                    by_signature.get(topology.signature, ()),
                    key=cls._identity,
                )
            )
            topology_rows.append(
                ExtremeNamedGearSetTopologyRealizationResult(
                    topology=topology,
                    realizations=realizations,
                    # These counts describe the reduced proof frontier, not raw source
                    # enumeration. Candidate-reduction provenance is carried explicitly
                    # on the outer result.
                    assignments_considered=len(realizations),
                    assignments_rejected=0,
                    truncated=False,
                    unresolved=(),
                )
            )

        realization = ExtremeNamedGearSetCatalogRealizationResult(
            topologies=tuple(topology_rows),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
        relevant = sum(
            1
            for row in relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.RELEVANT
        )
        unresolved_count = sum(
            1
            for row in relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
        )
        irrelevant = sum(
            1
            for row in relevance.evidence
            if row.status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
        )

        return ExtremeObjectiveNamedGearSetCatalogRealizationResult(
            objective_key="max_health",
            realization=realization,
            breakpoints_reviewed=len(relevance.evidence),
            breakpoints_retained_relevant=relevant,
            breakpoints_retained_unresolved=unresolved_count,
            breakpoints_pruned_irrelevant=irrelevant,
            breakpoints_pruned_equivalent=int(search.ordinary.equivalent_breakpoints_pruned),
            representative_limit_per_equivalence_class=int(search.ordinary.representative_limit),
            equivalence_reduction_proven=True,
            candidate_reduction_proven=bool(
                search.candidate_reduction_proven
                and dual_bar.denominator_proven
                and source_ids == admissible_ids
            ),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = ["ExtremeMaxHealthNamedGearRealizationAdapterService"]
