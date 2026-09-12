from __future__ import annotations

"""Adapt exact ordinary max-resource gear winners to the legacy realization contract.

Max Magicka and Max Stamina use the shared proof-reduced ordinary max-resource
search. This adapter exposes those exact winners through
``ExtremeObjectiveNamedGearSetCatalogRealizationResult`` while preserving the
canonical dual-bar admissibility audit and fail-closed proof semantics.

Max Health retains its dedicated adapter because conditional/search-state special
branches must be composed before the full named-gear denominator can close.
"""

from services.extreme_dual_bar_gear_state_catalog_service import (
    ExtremeDualBarGearStateCatalogService,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetTopologyCatalog
from services.extreme_max_resource_ordinary_named_gear_search_service import (
    ExtremeMaxResourceOrdinaryNamedGearSearchResult,
)
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationResult,
    ExtremeNamedGearSetTopologyRealizationResult,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)


class ExtremeMaxResourceNamedGearRealizationAdapterService:
    """Expose exact ordinary Magicka/Stamina winners through the legacy gear contract."""

    SUPPORTED_OBJECTIVES = frozenset({"max_magicka", "max_stamina"})

    @staticmethod
    def _identity(realization) -> tuple[object, ...]:
        return ExtremeDualBarGearStateCatalogService.realization_identity(realization)

    @classmethod
    def build(
        cls,
        *,
        search: ExtremeMaxResourceOrdinaryNamedGearSearchResult,
        topology_catalog: ExtremeGearSetTopologyCatalog,
        relevance: ExtremeGearSetObjectiveRelevanceCatalog,
    ) -> ExtremeObjectiveNamedGearSetCatalogRealizationResult:
        objective = str(relevance.objective_key or "").strip().casefold()
        if objective not in cls.SUPPORTED_OBJECTIVES:
            raise ValueError(
                "ordinary max-resource named-gear realization adapter supports only "
                "max_magicka and max_stamina"
            )
        if str(search.objective_key or "").strip().casefold() != objective:
            raise ValueError("search objective does not match relevance objective")

        unresolved: list[str] = list(search.unresolved)
        if search.special_or_nonflat_pairs:
            for set_id, name, piece_count in search.special_or_nonflat_pairs:
                unresolved.append(
                    f"{name} ({set_id}) breakpoint {piece_count} has a non-ordinary "
                    f"{objective} branch with no composed execution owner"
                )

        source = tuple(search.winning_realizations)
        source_denominator_proven = bool(
            search.full_named_gear_denominator_proven and not unresolved
        )
        dual_bar = ExtremeDualBarGearStateCatalogService.build(
            source,
            source_denominator_proven=source_denominator_proven,
            unresolved=tuple(unresolved),
        )
        admissible = dual_bar.admissible_realizations(active_bar="front")
        source_ids = {cls._identity(row) for row in source}
        admissible_ids = {cls._identity(row) for row in admissible}

        unresolved.extend(dual_bar.unresolved)
        if source_ids != admissible_ids:
            missing = len(source_ids - admissible_ids)
            extra = len(admissible_ids - source_ids)
            unresolved.append(
                f"Reduced {objective} named-gear frontier changed under canonical "
                f"dual-bar admissibility (missing={missing}, extra={extra})"
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
                    assignments_considered=len(realizations),
                    assignments_rejected=0,
                    truncated=False,
                    unresolved=(),
                )
            )

        final_unresolved = tuple(dict.fromkeys(item for item in unresolved if item))
        realization = ExtremeNamedGearSetCatalogRealizationResult(
            topologies=tuple(topology_rows),
            unresolved=final_unresolved,
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
            objective_key=objective,
            realization=realization,
            breakpoints_reviewed=len(relevance.evidence),
            breakpoints_retained_relevant=relevant,
            breakpoints_retained_unresolved=unresolved_count,
            breakpoints_pruned_irrelevant=irrelevant,
            breakpoints_pruned_equivalent=int(search.equivalent_breakpoints_pruned),
            representative_limit_per_equivalence_class=int(search.representative_limit),
            equivalence_reduction_proven=True,
            candidate_reduction_proven=bool(
                source_denominator_proven
                and dual_bar.denominator_proven
                and source_ids == admissible_ids
                and not final_unresolved
            ),
            unresolved=final_unresolved,
        )


__all__ = ["ExtremeMaxResourceNamedGearRealizationAdapterService"]
